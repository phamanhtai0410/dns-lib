# -*- coding: utf-8 -*-
"""
   Description:
        -
        -
"""


class MoralisChains:
    BSC = 'bsc'
    BSC_TESTNET = 'bsc testnet'
    ETHEREUM = 'eth'
    GOERLI = 'goerli'
    SEPOLIA = 'sepolia'
    POLYGON = 'polygon'


class Currencies:
    INZ = 'INZ'
    USDT = 'USDT'
    ETH = 'ETH'
    BNB = 'BNB'
    FIAT = 'FIAT'
    BUSD = 'BUSD'


SUPPORTED_CURRENCIES = [Currencies.USDT]


class Chains:
    AVAX = 'AVAX'
    BSC = 'BSC'
    ETHEREUM = 'ETHEREUM'
    POLYGON = 'POLYGON'
    SOLANA = 'SOLANA'
    BASE = 'BASE'
    SCROLL = 'SCROLL'
    ZKSYNC = 'ZKSYNC'
    AVAX = 'AVAX'


SUPPORTED_CHAINS = [Chains.BSC, Chains.BASE, Chains.ETHEREUM, Chains.SCROLL, Chains.ZKSYNC]
SUPPORTED_CHAIN_IDS = [
    56,  # BSC
    97,  # BSC TESTNET
    84531,  # BASE GOERLI
    1,  # ETHEREUM
    5,  # GOERLI
    534353,  # SCROLL TESTNET
    280,  # ZKSYNC TESTNET,
    43113, # AVAX TESTNET
    80001, # POLYGON TESTNET,
    420, # OP TESTNET
    421613, # ARB TESTNET
]


class TokenStandard:
    ERC20 = 'ERC20'
    ERC721 = 'ERC721'
    ERC1155 = 'ERC1155'
    ERC777 = 'ERC777'


class ContractInsertType:
    CREATE = 'CREATE'
    IMPORT = 'IMPORT'


class TaskStatus:
    PENDING = 'PENDING'
    PROCESSING = 'PROCESSING'
    DONE = 'DONE'
    FAIL = 'FAIL'
