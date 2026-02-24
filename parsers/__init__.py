"""
Parsers para convertir CSV nativos de bancos a formato unificado.
"""
from .base import BankParser
from .openbank import OpenbankParser
from .myinvestor import MyInvestorParser
from .mediolanum import MediolanumParser
from .revolut import RevolutParser
from .trade_republic import TradeRepublicParser
from .trade_republic_pdf import TradeRepublicPDFParser
from .b100 import B100Parser
from .abanca import AbancaParser
from .preprocessed import PreprocessedParser
from .bankinter import BankinterParser

__all__ = [
    'BankParser',
    'OpenbankParser',
    'MyInvestorParser',
    'MediolanumParser',
    'RevolutParser',
    'TradeRepublicParser',
    'TradeRepublicPDFParser',
    'B100Parser',
    'AbancaParser',
    'PreprocessedParser',
    'BankinterParser',
]
