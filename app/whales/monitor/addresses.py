# app/whales/monitor/addresses.py
"""
Exchange and Bridge Address Lists
"""

from typing import Set


class AddressManager:
    """Управление адресами бирж и мостов"""
    
    @staticmethod
    def get_exchange_addresses() -> Set[str]:
        """Возвращает список адресов бирж"""
        return {
            "0x28c6c06298d514db089934071355e5743bf21d60",
            "0x21a31ee1afc51d94c2efccaa2092ad1028285549",
            "0xdfd5293d8e347dfe59e90efd55b2956a1343963d",
            "0x564286362092d8e7936f0549571a803b203aaced",
            "0x0681d8db095565fe8a346fa0277bffde9c0edbbf",
            "0x71660c4005ba85c37ccec55d0c4493e66fe775d3",
            "0x503828976d22510aad0201ac7ec88293211d23da",
            "0xddfabcdc4d8ffc6d5beaf154f18b778f892a0740",
            "0xa090e606e30bd747d4e6245a1517ebe430f0057e",
            "0x2910543af39aba0cd09dbb2d50200b3e800a63d2",
            "0x0a869d79a7052c7f1b55a8ebabbea3420f0d1e13",
            "0xe853c56864a2ebe4576a807d26fdc4a0ada51919",
            "0x1151314c646ce4e0efd76d1af4760ae66a9fe30f",
            "0x876eabf441b2ee5b5b0554fd502a8e0600950cfa",
            "0x98ec059dc3adfbdd63429454aeb0c990fba4a128",
            "0x6cc5f688a315f3dc28a7781717a9a798a59fda7b",
            "0xf89d7b9c864f589bbf53a82105107622b35eaa40",
            "0x1c4b70a3968436b9a0a9cf5205c787eb81bb558c",
            "0xab5c66752a9e8167967685f1450532fb96d5d24f",
            "0x2b5634c42055806a59e9107ed44d43c426e58258"
        }
    
    @staticmethod
    def get_bridge_addresses() -> Set[str]:
        """Возвращает список адресов мостов"""
        return {
            "0x6b7a87899490ece95443e979ca9485cbe7e71522",
            "0x5427fefa711eff984124bfbb1ab6fbf5e3da1820",
            "0x2796317b0ff8538f253012862c06787adfb8ceb6",
            "0xc186fa914353c44b2e33ebe05f21846f1048beda",
            "0x3666f603cc164936c1b87e207f36babaa41b67aa",
            "0x8731d54e9d02c286767d56ac03e8037c07e01e98",
            "0x66a71dcef29a0ffbdbe3c6a460a3b5bc225cd675"
        }