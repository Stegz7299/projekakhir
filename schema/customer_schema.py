from pydantic import BaseModel

# Schema for creating a customer (input)
class CustomerIn(BaseModel):
    name: str
    address: str

    class Config:
        orm_mode = True  # Converts from ORM model to Pydantic model

# Schema for updating a customer (input)
class CustomerUpdate(BaseModel):
    name: str
    address: str

    class Config:
        orm_mode = True

# Schema for getting a customer (output)
class CustomerOut(BaseModel):
    id: int
    name: str
    address: str

    class Config:
        orm_mode = True
