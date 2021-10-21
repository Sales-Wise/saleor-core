import logging
import os
from typing import List

from ....order.models import Fulfillment
from ... import PaymentError, TransactionKind
from ...interface import GatewayConfig, GatewayResponse, PaymentData
from ...models import Payment
from . import api
from .api_types import ApiConfig, PaymentStatus, get_api_config
from .utils import get_payment_name, notify_dashboard

logger = logging.getLogger(__name__)


def inject_api_config(fun):
    def inner(payment_information: PaymentData, config: GatewayConfig):
        return fun(payment_information, get_api_config(config.connection_params))

    return inner


def parse_errors(errors: List[str]) -> str:
    # FIXME: better solution?
    #  Transaction.error in database has max_length of 256
    return os.linesep.join(errors)[:256]


@inject_api_config
def process_payment(
    payment_information: PaymentData, config: ApiConfig
) -> GatewayResponse:
    result = api.register_transaction(config, payment_information)

    return GatewayResponse(
        is_success=result.status == PaymentStatus.SUCCESS,
        action_required=False,
        kind=TransactionKind.CAPTURE,
        amount=payment_information.amount,
        currency=payment_information.currency,
        transaction_id=result.psp_reference,
        error=parse_errors(result.errors),
        raw_response=result.raw_response,
        psp_reference=result.psp_reference,
    )


@inject_api_config
def capture(payment_information: PaymentData, config: ApiConfig) -> GatewayResponse:
    raise NotImplementedError


@inject_api_config
def void(payment_information: PaymentData, config: ApiConfig) -> GatewayResponse:
    raise NotImplementedError


@inject_api_config
def tracking_number_updated(fulfillment: Fulfillment, config: ApiConfig) -> None:
    from .plugin import NPAtobaraiGatewayPlugin

    order = fulfillment.order
    payments = order.payments.filter(
        gateway=NPAtobaraiGatewayPlugin.PLUGIN_ID, is_active=True
    )

    if payments:
        results = [
            api.report_fulfillment(config, payment, fulfillment) for payment in payments
        ]
    else:
        results = [("", ["No active payments for this order"], False)]

    for payment_id, errors, already_captured in results:
        payment_name = get_payment_name(payment_id)

        if already_captured:
            logger.warning("Payment was already captured")
            notify_dashboard(
                order, f"Error: {payment_name.capitalize()} was already captured"
            )
        elif errors:
            error = ", ".join(errors)
            logger.warning(
                "Could not capture %s in NP Atobarai: %s", payment_name, error
            )
            notify_dashboard(order, f"Capture Error for {payment_name}")
        else:
            notify_dashboard(order, f"Captured {payment_name}")


@inject_api_config
def refund(payment_information: PaymentData, config: ApiConfig) -> GatewayResponse:
    payment_id = payment_information.payment_id
    payment = Payment.objects.filter(pk=payment_id).first()

    if not payment:
        raise PaymentError(f"Payment with id {payment_id} does not exist.")
    if payment_information.amount < payment.captured_amount:
        raise PaymentError(f"Cannot partially refund payment with id {payment_id}")

    result = api.cancel_transaction(config, payment_information)

    return GatewayResponse(
        is_success=result.status == PaymentStatus.SUCCESS,
        action_required=False,
        kind=TransactionKind.REFUND,
        amount=payment_information.amount,
        currency=payment_information.currency,
        transaction_id=result.psp_reference,
        error=os.linesep.join(result.errors),
        raw_response=result.raw_response,
        psp_reference=result.psp_reference,
    )
