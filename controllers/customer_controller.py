from fastapi import APIRouter, HTTPException
from model import customer_model
from schema.customer_schema import CustomerOut, CustomerIn, CustomerUpdate

router = APIRouter()

@router.get("/customers", response_model=list[CustomerOut])
def get_all_customers():
    customers = customer_model.get_all_customers()
    return customers

@router.get("/customers/{customer_id}", response_model=CustomerOut)
def get_customer(customer_id: int):
    customer = customer_model.get_customer_by_id(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer

@router.post("/customers", status_code=201, response_model=CustomerOut)
def create_customer(customer: CustomerIn):
    new_id = customer_model.create_customer(customer.name, customer.address)
    if not new_id:
        raise HTTPException(status_code=400, detail="Failed to create customer")
    return customer_model.get_customer_by_id(new_id)

@router.put("/customers/{customer_id}", response_model=CustomerOut)
def update_customer(customer_id: int, customer: CustomerUpdate):
    updated = customer_model.update_customer(customer_id, customer.name, customer.address)
    if updated == 0:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer_model.get_customer_by_id(customer_id)

@router.delete("/customers/{customer_id}")
def delete_customer(customer_id: int):
    deleted = customer_model.delete_customer(customer_id)
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Customer not found")
    return {"message": "Customer deleted"}
