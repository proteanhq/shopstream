"""FastAPI endpoints for the Identity domain."""

from fastapi import APIRouter
from protean.utils.globals import current_domain

from identity.api.schemas import (
    AddAddressRequest,
    CustomerIdResponse,
    RegisterCustomerRequest,
    StatusResponse,
    SuspendAccountRequest,
    UpdateAddressRequest,
    UpdateProfileRequest,
    UpgradeTierRequest,
)
from identity.customer.account import CloseAccount, ReactivateAccount, SuspendAccount
from identity.customer.addresses import (
    AddAddress,
    RemoveAddress,
    SetDefaultAddress,
    UpdateAddress,
)
from identity.customer.profile import UpdateProfile
from identity.customer.registration import RegisterCustomer
from identity.customer.tier import UpgradeTier

router = APIRouter(prefix="/customers", tags=["customers"])


@router.post("", status_code=201, response_model=CustomerIdResponse)
async def register_customer(body: RegisterCustomerRequest) -> CustomerIdResponse:
    command = RegisterCustomer(
        external_id=body.external_id,
        email=body.email,
        first_name=body.first_name,
        last_name=body.last_name,
        phone=body.phone,
        date_of_birth=body.date_of_birth,
    )
    result = current_domain.process(command, asynchronous=False)
    return CustomerIdResponse(customer_id=result)


@router.put("/{customer_id}/profile", response_model=StatusResponse)
async def update_profile(customer_id: str, body: UpdateProfileRequest) -> StatusResponse:
    command = UpdateProfile(
        customer_id=customer_id,
        first_name=body.first_name,
        last_name=body.last_name,
        phone=body.phone,
        date_of_birth=body.date_of_birth,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@router.post("/{customer_id}/addresses", status_code=201, response_model=StatusResponse)
async def add_address(customer_id: str, body: AddAddressRequest) -> StatusResponse:
    command = AddAddress(
        customer_id=customer_id,
        label=body.label,
        street=body.street,
        city=body.city,
        state=body.state,
        postal_code=body.postal_code,
        country=body.country,
        geo_lat=body.geo_lat,
        geo_lng=body.geo_lng,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@router.put("/{customer_id}/addresses/{address_id}", response_model=StatusResponse)
async def update_address(customer_id: str, address_id: str, body: UpdateAddressRequest) -> StatusResponse:
    command = UpdateAddress(
        customer_id=customer_id,
        address_id=address_id,
        label=body.label,
        street=body.street,
        city=body.city,
        state=body.state,
        postal_code=body.postal_code,
        country=body.country,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@router.delete("/{customer_id}/addresses/{address_id}", response_model=StatusResponse)
async def remove_address(customer_id: str, address_id: str) -> StatusResponse:
    command = RemoveAddress(
        customer_id=customer_id,
        address_id=address_id,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@router.put("/{customer_id}/addresses/{address_id}/default", response_model=StatusResponse)
async def set_default_address(customer_id: str, address_id: str) -> StatusResponse:
    command = SetDefaultAddress(
        customer_id=customer_id,
        address_id=address_id,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@router.put("/{customer_id}/suspend", response_model=StatusResponse)
async def suspend_account(customer_id: str, body: SuspendAccountRequest) -> StatusResponse:
    command = SuspendAccount(
        customer_id=customer_id,
        reason=body.reason,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@router.put("/{customer_id}/reactivate", response_model=StatusResponse)
async def reactivate_account(customer_id: str) -> StatusResponse:
    command = ReactivateAccount(customer_id=customer_id)
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@router.put("/{customer_id}/close", response_model=StatusResponse)
async def close_account(customer_id: str) -> StatusResponse:
    command = CloseAccount(customer_id=customer_id)
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@router.put("/{customer_id}/tier", response_model=StatusResponse)
async def upgrade_tier(customer_id: str, body: UpgradeTierRequest) -> StatusResponse:
    command = UpgradeTier(
        customer_id=customer_id,
        new_tier=body.new_tier,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse()
