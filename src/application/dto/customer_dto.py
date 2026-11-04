"""Customer output model of the use cases."""

from dataclasses import dataclass

from src.domain.entities.customer import Customer


@dataclass(frozen=True, slots=True)
class CustomerDTO:
    id: str
    name: str
    email: str
    company: str
    plan: str

    @classmethod
    def from_entity(cls, customer: Customer) -> "CustomerDTO":
        return cls(
            id=customer.id,
            name=customer.name,
            email=customer.email,
            company=customer.company,
            plan=customer.plan,
        )
