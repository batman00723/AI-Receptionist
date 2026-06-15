from ninja_extra import NinjaExtraAPI

from .document_controller import DocumentOperationController, ChatOperationController, TwilioWebHookController, PingPongOperationController

api_v1 = NinjaExtraAPI(version="1.0.0")

api_v1.register_controllers(DocumentOperationController, ChatOperationController, TwilioWebHookController, PingPongOperationController)

