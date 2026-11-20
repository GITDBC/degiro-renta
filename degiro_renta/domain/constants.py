# Standard libraries
from typing import Final

# Listed securities whose legal form is debt rather than equity, so the
# result of transmitting them is capital income of art. 25.2.b LIRPF
# instead of a capital gain: art. 91.1 RIRPF makes financial assets the
# "valores negociables representativos de la captación y utilización de
# capitales ajenos". An ISIN prefix cannot tell them apart, so they are
# listed one by one with the document that supports it.
# XS2940466316 (iShares Bitcoin ETP): its KID describes it as "secured
# debt securities", not units of a collective investment scheme. The DGT
# classified an analogous ETC (secured debt security issued by a special
# purpose vehicle) as art. 25.2.b capital income in V0267-25. No ruling
# on this ISIN has been found, so the criterion rests on the KID, the
# regulation and that analogy.
DEBT_SECURITY_ISINS: Final[frozenset[str]] = frozenset({"XS2940466316"})
