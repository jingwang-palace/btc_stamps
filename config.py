import os
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
import decimal
import regex
import sqlite3
import time
import math
import requests
from requests.exceptions import Timeout, ReadTimeout, ConnectionError
import concurrent.futures
import logging
import json
import concurrent.futures
import collections
import binascii
import hashlib
import threading
import util




logger = logging.getLogger(__name__)
RPC_USER = os.environ.get("RPC_USER", 'rpc')
RPC_PASSWORD = os.environ.get("RPC_PASSWORD", 'rpc')
RPC_IP = os.environ.get("RPC_IP", '127.0.0.1')
RPC_PORT = os.environ.get("RPC_PORT",'8332')
RPC_URL = f"http://{RPC_USER}:{RPC_PASSWORD}@{RPC_IP}:{RPC_PORT}"
RPC_CONNECTION = AuthServiceProxy(RPC_URL)


# RPC_TOKEN = '94c84a27439d2148c3d7b521a3ea638a6cb9469b'
# RPC_URL = f"https://thrilling-dimensional-research.quiknode.pro/{RPC_TOKEN}/"
# assert 'RPC_URL' in globals(), "RPC_URL is not defined"
# RPC_CONNECTION = AuthServiceProxy(RPC_URL)
# print(RPC_CONNECTION.getblockcount())


RAW_TRANSACTIONS_CACHE_SIZE = 20000
RPC_BATCH_SIZE = 20     # A 1 MB block can hold about 4200 transactions.
RPC_BATCH_NUM_WORKERS = 5 #20

raw_transactions_cache = util.DictCache(size=RAW_TRANSACTIONS_CACHE_SIZE)  # used in getrawtransaction_batch()



STAMP_PREFIX_HEX = "7374616d703a" # (lowercase stamp:)

STAMP_GENESIS_BLOCK = 793068 # block height of first stamp transaction

BYTE_LENGTH_PREFIX_SIZE = 2 # 2 bytes for byte length prefix after block 790370

TESTNET = None
REGTEST = None

STAMP_PREFIX = "7374616d703a" # (lowercase stamp:) 

BURNKEYS = [
    "022222222222222222222222222222222222222222222222222222222222222222",
    "033333333333333333333333333333333333333333333333333333333333333333",
    "020202020202020202020202020202020202020202020202020202020202020202",
    "030303030303030303030303030303030303030303030303030303030303030302",
    "030303030303030303030303030303030303030303030303030303030303030303"
]


TICK_PATTERN_LIST = {
    regex.compile(r'((\p{Emoji_Presentation})|(\p{Emoji_Modifier_Base}\p{Emoji_Modifier}?))|[\p{Punctuation}\p{Symbol}\w~!@#$%^&*()_=<>?]')
}

# part of addrindexrs
# def chunkify(l, n):
#     n = max(1, n)
#     return [l[i:i + n] for i in range(0, len(l), n)]

def decimal_default(obj):
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    raise TypeError

# def get_db_connection():
#     conn = sqlite3.connect('blockchain.db')
#     return conn



def bitcoin_rpc_call(method, *params):
    """Calls a Bitcoin Core RPC method and returns the response"""
    MAX_TRIES = 12
    INITIAL_WAIT = 5

    for i in range(MAX_TRIES):
        try:
            response = getattr(RPC_CONNECTION, method)(*params)
            if i > 0:
                print('Successfully connected.')
            return response
        except (JSONRPCException, ConnectionRefusedError):
            if i == MAX_TRIES - 1:
                print('Maximum retries reached. Exiting.')
                raise
            wait_time = INITIAL_WAIT * math.pow(2, i)
            print('Could not connect to backend at `{}`. (Try {}/{}, waiting {} seconds)'.format(RPC_IP, i+1, MAX_TRIES, wait_time))
            time.sleep(wait_time)

    raise Exception('Cannot communicate with bitcoin core at `{}`.'.format(RPC_IP))


def bitcoin_rpc_batch(request_list):
    """Sends multiple Bitcoin Core RPC requests in parallel and returns the responses"""
    CHUNK_SIZE = 10

    def make_call(chunk):
        responses = [getattr(RPC_CONNECTION, req['method'])(*req['params']) for req in chunk]
        return responses

    chunks = [request_list[i:i+CHUNK_SIZE] for i in range(0, len(request_list), CHUNK_SIZE)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        responses = list(executor.map(make_call, chunks))

    return [response for chunk in responses for response in chunk]





### THIS IS FOR PARSE STAMP
def getrawtransaction(tx_hash, verbose=False, skip_missing=False):
    """Returns the raw transaction for a given transaction hash **verbose=False is the hex only"""
    if skip_missing and tx_hash not in getrawtransaction_batch([tx_hash], skip_missing=True):
        return None

    response = bitcoin_rpc_call('getrawtransaction', tx_hash, verbose)
    if skip_missing and response is None:
        return None

    return response['hex'] if not verbose else response

## THIS IS FOR PARSE STAMP
def getrawtransaction_batch(txhash_list, verbose=False, skip_missing=False):
    """Returns the raw transactions for a list of transaction hashes"""
    txhash_dict = {}
    cached_txhashes = set(txhash_list) & set(txhash_dict.keys())
    uncached_txhashes = set(txhash_list) - cached_txhashes

    # Get cached transactions
    for tx_hash in cached_txhashes:
        txhash_dict[tx_hash] = txhash_dict[tx_hash]

    # Get uncached transactions
    if uncached_txhashes:
        responses = bitcoin_rpc_batch([{'method': 'getrawtransaction', 'params': [tx_hash, verbose]} for tx_hash in uncached_txhashes])

        for i, response in enumerate(responses):
            tx_hash = uncached_txhashes[i]
            if skip_missing and response is None:
                continue
            txhash_dict[tx_hash] = response['hex'] if not verbose else response

    return txhash_dict

# def bitcoin_getblock(blockhash):
#     """Returns information about a Bitcoin block"""
#     return bitcoin_rpc_call('getblock', blockhash)


UNIT = 100000000        # The same across assets.


# Versions
VERSION_MAJOR = 9
VERSION_MINOR = 60
VERSION_REVISION = 2
VERSION_STRING = str(VERSION_MAJOR) + '.' + str(VERSION_MINOR) + '.' + str(VERSION_REVISION)


# Counterparty protocol
TXTYPE_FORMAT = '>I'
SHORT_TXTYPE_FORMAT = 'B'

TWO_WEEKS = 2 * 7 * 24 * 3600
MAX_EXPIRATION = 4 * 2016   # Two months

MEMPOOL_BLOCK_HASH = 'mempool'
MEMPOOL_BLOCK_INDEX = 9999999


# SQLite3
MAX_INT = 2**63 - 1


# Bitcoin Core
OP_RETURN_MAX_SIZE = 80  # bytes


# Currency agnosticism
BTC = 'BTC'
XCP = 'XCP'

BTC_NAME = 'Bitcoin'
XCP_NAME = 'btc_stamps'
APP_NAME = XCP_NAME.lower()


DEFAULT_BACKEND_PORT_REGTEST = 28332
DEFAULT_BACKEND_PORT_TESTNET = 18332
DEFAULT_BACKEND_PORT = 8332

DEFAULT_INDEXD_PORT_REGTEST = 28432
DEFAULT_INDEXD_PORT_TESTNET = 18432
DEFAULT_INDEXD_PORT = 8432

UNSPENDABLE_REGTEST = 'mvCounterpartyXXXXXXXXXXXXXXW24Hef'
UNSPENDABLE_TESTNET = 'mvCounterpartyXXXXXXXXXXXXXXW24Hef'
UNSPENDABLE_MAINNET = '1CounterpartyXXXXXXXXXXXXXXXUWLpVr'

ADDRESSVERSION_TESTNET = b'\x6f'
P2SH_ADDRESSVERSION_TESTNET = b'\xc4'
PRIVATEKEY_VERSION_TESTNET = b'\xef'
ADDRESSVERSION_MAINNET = b'\x00'
P2SH_ADDRESSVERSION_MAINNET = b'\x05'
PRIVATEKEY_VERSION_MAINNET = b'\x80'
ADDRESSVERSION_REGTEST = b'\x6f'
P2SH_ADDRESSVERSION_REGTEST = b'\xc4'
PRIVATEKEY_VERSION_REGTEST = b'\xef'
MAGIC_BYTES_TESTNET = b'\xfa\xbf\xb5\xda'   # For bip-0010
MAGIC_BYTES_MAINNET = b'\xf9\xbe\xb4\xd9'   # For bip-0010
MAGIC_BYTES_REGTEST = b'\xda\xb5\xbf\xfa'

BLOCK_FIRST_TESTNET_TESTCOIN = 310000
BURN_START_TESTNET_TESTCOIN = 310000
BURN_END_TESTNET_TESTCOIN = 4017708     # Fifty years, at ten minutes per block.

BLOCK_FIRST_TESTNET = 310000
BLOCK_FIRST_TESTNET_HASH = '000000001f605ec6ee8d2c0d21bf3d3ded0a31ca837acc98893876213828989d'
BURN_START_TESTNET = 310000
BURN_END_TESTNET = 4017708              # Fifty years, at ten minutes per block.

BLOCK_FIRST_MAINNET_TESTCOIN = 278270
BURN_START_MAINNET_TESTCOIN = 278310
BURN_END_MAINNET_TESTCOIN = 2500000     # A long time.

BLOCK_FIRST_MAINNET = 779650
BLOCK_FIRST_MAINNET_HASH = '000000000000000000058ea4f7bf747a78475f137fd8ff5f22b8db1f6dc1a8c2'
# FIRST MAINNET BLOCK WITH BTCSTAMPS: 793487 TX 50aeb77245a9483a5b077e4e7506c331dc2f628c22046e7d2b4c6ad6c6236ae1
BURN_START_MAINNET = 278310
BURN_END_MAINNET = 283810

BLOCK_FIRST_REGTEST = 0
BLOCK_FIRST_REGTEST_HASH = '0f9188f13cb7b2c71f2a335e3a4fc328bf5beb436012afca590b1a11466e2206'
BURN_START_REGTEST = 101
BURN_END_REGTEST = 150000000

BLOCK_FIRST_REGTEST_TESTCOIN = 0
BURN_START_REGTEST_TESTCOIN = 101
BURN_END_REGTEST_TESTCOIN = 150

# Protocol defaults
# NOTE: If the DUST_SIZE constants are changed, they MUST also be changed in counterblockd/lib/config.py as well
DEFAULT_REGULAR_DUST_SIZE = 546          # TODO: Revisit when dust size is adjusted in bitcoin core
DEFAULT_MULTISIG_DUST_SIZE = 7800        # <https://bitcointalk.org/index.php?topic=528023.msg7469941#msg7469941>
DEFAULT_OP_RETURN_VALUE = 0
DEFAULT_FEE_PER_KB_ESTIMATE_SMART = 1024
DEFAULT_FEE_PER_KB = 25000               # sane/low default, also used as minimum when estimated fee is used
ESTIMATE_FEE_PER_KB = True               # when True will use `estimatesmartfee` from bitcoind instead of DEFAULT_FEE_PER_KB
ESTIMATE_FEE_CONF_TARGET = 3
ESTIMATE_FEE_MODE = 'CONSERVATIVE'

# UI defaults
DEFAULT_FEE_FRACTION_REQUIRED = .009   # 0.90%
DEFAULT_FEE_FRACTION_PROVIDED = .01    # 1.00%


DEFAULT_REQUESTS_TIMEOUT = 20   # 20 seconds
DEFAULT_RPC_BATCH_SIZE = 20     # A 1 MB block can hold about 4200 transactions.

# Custom exit codes
EXITCODE_UPDATE_REQUIRED = 5


DEFAULT_CHECK_ASSET_CONSERVATION = True

BACKEND_RAW_TRANSACTIONS_CACHE_SIZE = 20000
BACKEND_RPC_BATCH_NUM_WORKERS = 6

UNDOLOG_MAX_PAST_BLOCKS = 100 #the number of past blocks that we store undolog history

DEFAULT_UTXO_LOCKS_MAX_ADDRESSES = 1000
DEFAULT_UTXO_LOCKS_MAX_AGE = 3.0 #in seconds

ADDRESS_OPTION_REQUIRE_MEMO = 1
ADDRESS_OPTION_MAX_VALUE = ADDRESS_OPTION_REQUIRE_MEMO # Or list of all the address options
OLD_STYLE_API = True

API_LIMIT_ROWS = 1000

MPMA_LIMIT = 1000

MEMPOOL_TXCOUNT_UPDATE_LIMIT=60000