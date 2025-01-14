from ....permission.enums import ProductPermissions
from ....warehouse import models
from ...account.i18n import I18nMixin
from ...core import ResolveInfo
from ...core.mutations import ModelMutation
from ...core.types import WarehouseError
from ...plugins.dataloaders import get_plugin_manager_promise
from ..types import Warehouse, WarehouseCreateInput
from .base import WarehouseMixin


class WarehouseCreate(WarehouseMixin, ModelMutation, I18nMixin):
    class Arguments:
        input = WarehouseCreateInput(
            required=True, description="Fields required to create warehouse."
        )

    class Meta:
        description = "Creates new warehouse."
        model = models.Warehouse
        object_type = Warehouse
        permissions = (ProductPermissions.MANAGE_PRODUCTS,)
        error_type_class = WarehouseError
        error_type_field = "warehouse_errors"

    @classmethod
    def prepare_address(cls, cleaned_data, *args):
        address_form = cls.validate_address_form(cleaned_data["address"])
        return address_form.save()

    @classmethod
    def post_save_action(cls, info: ResolveInfo, instance, cleaned_input):
        manager = get_plugin_manager_promise(info.context).get()
        cls.call_event(manager.warehouse_created, instance)
