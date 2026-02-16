"""FastAPI endpoints for the Identity domain."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from protean.utils.globals import current_domain

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


@router.post("", status_code=201)
async def register_customer(request: Request):
    payload = await request.json()
    command = RegisterCustomer(
        external_id=payload["external_id"],
        email=payload["email"],
        first_name=payload["first_name"],
        last_name=payload["last_name"],
        phone=payload.get("phone"),
        date_of_birth=payload.get("date_of_birth"),
    )
    result = current_domain.process(command, asynchronous=False)
    return JSONResponse(status_code=201, content={"customer_id": result})


@router.put("/{customer_id}/profile")
async def update_profile(customer_id: str, request: Request):
    payload = await request.json()
    command = UpdateProfile(
        customer_id=customer_id,
        first_name=payload["first_name"],
        last_name=payload["last_name"],
        phone=payload.get("phone"),
        date_of_birth=payload.get("date_of_birth"),
    )
    current_domain.process(command, asynchronous=False)
    return JSONResponse(status_code=200, content={"status": "ok"})


@router.post("/{customer_id}/addresses", status_code=201)
async def add_address(customer_id: str, request: Request):
    payload = await request.json()
    command = AddAddress(
        customer_id=customer_id,
        label=payload.get("label"),
        street=payload["street"],
        city=payload["city"],
        state=payload.get("state"),
        postal_code=payload["postal_code"],
        country=payload["country"],
        geo_lat=payload.get("geo_lat"),
        geo_lng=payload.get("geo_lng"),
    )
    current_domain.process(command, asynchronous=False)
    return JSONResponse(status_code=201, content={"status": "ok"})


@router.put("/{customer_id}/addresses/{address_id}")
async def update_address(customer_id: str, address_id: str, request: Request):
    payload = await request.json()
    command = UpdateAddress(
        customer_id=customer_id,
        address_id=address_id,
        label=payload.get("label"),
        street=payload.get("street"),
        city=payload.get("city"),
        state=payload.get("state"),
        postal_code=payload.get("postal_code"),
        country=payload.get("country"),
    )
    current_domain.process(command, asynchronous=False)
    return JSONResponse(status_code=200, content={"status": "ok"})


@router.delete("/{customer_id}/addresses/{address_id}")
async def remove_address(customer_id: str, address_id: str):
    command = RemoveAddress(
        customer_id=customer_id,
        address_id=address_id,
    )
    current_domain.process(command, asynchronous=False)
    return JSONResponse(status_code=200, content={"status": "ok"})


@router.put("/{customer_id}/addresses/{address_id}/default")
async def set_default_address(customer_id: str, address_id: str):
    command = SetDefaultAddress(
        customer_id=customer_id,
        address_id=address_id,
    )
    current_domain.process(command, asynchronous=False)
    return JSONResponse(status_code=200, content={"status": "ok"})


@router.put("/{customer_id}/suspend")
async def suspend_account(customer_id: str, request: Request):
    payload = await request.json()
    command = SuspendAccount(
        customer_id=customer_id,
        reason=payload["reason"],
    )
    current_domain.process(command, asynchronous=False)
    return JSONResponse(status_code=200, content={"status": "ok"})


@router.put("/{customer_id}/reactivate")
async def reactivate_account(customer_id: str):
    command = ReactivateAccount(customer_id=customer_id)
    current_domain.process(command, asynchronous=False)
    return JSONResponse(status_code=200, content={"status": "ok"})


@router.put("/{customer_id}/close")
async def close_account(customer_id: str):
    command = CloseAccount(customer_id=customer_id)
    current_domain.process(command, asynchronous=False)
    return JSONResponse(status_code=200, content={"status": "ok"})


@router.put("/{customer_id}/tier")
async def upgrade_tier(customer_id: str, request: Request):
    payload = await request.json()
    command = UpgradeTier(
        customer_id=customer_id,
        new_tier=payload["new_tier"],
    )
    current_domain.process(command, asynchronous=False)
    return JSONResponse(status_code=200, content={"status": "ok"})
