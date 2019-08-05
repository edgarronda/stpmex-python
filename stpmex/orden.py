import random
import time
import unicodedata
from dataclasses import field
from typing import Optional, Type

import clabe
from pydantic import PositiveFloat, constr, validator
from pydantic.dataclasses import dataclass

from .types import Prioridad, TipoCuenta

STP_BANK_CODE = '90646'


def truncated_str(length) -> Type:
    return constr(strip_whitespace=True, min_length=1, curtail_length=length)


def digits(
    min_length: Optional[int] = None, max_length: Optional[int] = None
) -> Type:
    return constr(regex=r'^\d+$', min_length=min_length, max_length=max_length)


@dataclass
class Orden:
    monto: PositiveFloat
    conceptoPago: truncated_str(39)

    nombreBeneficiario: truncated_str(39)
    cuentaBeneficiario: digits(10, 19)
    institucionContraparte: digits(5, 5)
    tipoCuentaBeneficiario: int

    nombreOrdenante: Optional[truncated_str(39)] = None
    cuentaOrdenante: Optional[digits(10, 19)] = None
    institucionOperante: digits(5, 5) = STP_BANK_CODE
    tipoCuentaOrdenante: Optional[int] = None

    claveRastreo: truncated_str(29) = field(
        default_factory=lambda: f'CR{int(time.time())}'
    )
    referenciaNumerica: digits(1, 7) = field(
        default_factory=lambda: random.randint(10 ** 6, 10 ** 7)
    )
    rfcCurpBeneficiario: constr(max_length=18) = 'ND'
    rfcCurpOrdenante: Optional[constr(max_length=18)] = None
    medioEntrega: int = 3
    prioridad: int = Prioridad.alta.value
    tipoPago: int = 1
    topologia: str = 'T'
    iva: Optional[float] = None

    def __post_init__(self):
        # Test before Pydantic coerces it to a float
        if not isinstance(self.monto, float):
            raise ValueError('monto must be a float')

    @validator('cuentaBeneficiario', 'cuentaOrdenante')
    def __validate_cuenta(cls, v):
        if len(v) == 18:
            if not clabe.validate_clabe(v):
                raise ValueError('cuenta no es una válida CLABE')
        elif not len(v) in {10, 15, 16}:
            raise ValueError('cuenta no es válida')
        return v

    @validator('institucionContraparte', 'institucionOperante')
    def __validate_institucion(cls, v):
        if v not in clabe.BANKS.values():
            raise ValueError(f'{v} no se corresponde a un banco')
        return v

    @validator('tipoCuentaBeneficiario')
    def __validate_tipoCuenta(cls, v, values, **kwargs):
        try:
            cuenta = values['cuentaBeneficiario']
        except KeyError:  # there's a validation error elsewhere
            return v
        if not any(
            [
                len(cuenta) == 10 and v == TipoCuenta.phone_number.value,
                len(cuenta) in {15, 16} and v == TipoCuenta.card.value,
                len(cuenta) == 18 and v == TipoCuenta.clabe.value,
            ]
        ):
            raise ValueError('tipoCuenta no es válido')
        return v

    @validator('nombreBeneficiario', 'nombreOrdenante', 'conceptoPago')
    def __unicode_to_ascii(cls, v):
        v = unicodedata.normalize('NFKD', v).encode('ascii', 'ignore')
        return v.decode('ascii')