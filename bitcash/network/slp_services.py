import logging
import json

import requests
import base64
from decimal import Decimal

from bitcash.network import currency_to_satoshi
from bitcash.network.meta import Unspent
from bitcash.network.transaction import Transaction, TxPart

DEFAULT_TIMEOUT = 30

BCH_TO_SAT_MULTIPLIER = 100000000


class SlpAPI():
    SLP_MAIN_ENDPOINT = 'https://slpdb.fountainhead.cash/q/'

    @classmethod
    def query_to_url(cls, query):
        
        query_to_string = json.dumps(query)
        b64 = base64.b64encode(query_to_string.encode("utf-8"))
        path = str(b64)
        path = path[2:-1]

        url = cls.SLP_MAIN_ENDPOINT + path

        return url

    @classmethod
    def get_balance(cls, address, tokenId=None, limit=100, skip=0):
        # address = "simpleledger:qpt8z56sjcng8eux4pgvl7msnns2fzj05s89rl7w90"
        # tokenId = "7f27766677948e02aca409bf344632f3e8e350105017ef14d88fc2c048347146"

        if tokenId:
            query = {
                "v": 3,
                "q": {
                    "db": ["g"],
                    "aggregate": [
                    {
                        "$match": {
                        "graphTxn.outputs.address": address
                        }
                    },
                    {
                        "$unwind": "$graphTxn.outputs"
                    },
                    {
                        "$match": {
                        "graphTxn.outputs.status": "UNSPENT",
                        "graphTxn.outputs.address": address
                        }
                    },
                    
                    {
                        "$group": {
                        "_id": "$tokenDetails.tokenIdHex",
                        "slpAmount": {
                            "$sum": "$graphTxn.outputs.slpAmount"
                        }
                        }
                    },
                    {
                        "$sort": {
                        "slpAmount": -1
                        }
                    },
                    {
                        "$match": {
                        "slpAmount": {
                            "$gt": 0
                        }
                        }
                    },
                    {
                        "$lookup": {
                        "from": "tokens",
                        "localField": "_id",
                        "foreignField": "tokenDetails.tokenIdHex",
                        "as": "token"
                        }
                    },
                    {
                        "$match": {
                        "_id": tokenId
                        }
                    }
                    ],
                    "sort": {
                    "slpAmount": -1
                    },
                    "skip": 0,
                    "limit": 10
                 }
                }

            path = cls.query_to_url(query)
            r = requests.get(url = path, timeout=DEFAULT_TIMEOUT)
            j = r.json()['g']

            return [
                
                (
                a['token'][0]['tokenDetails']['name'],
                a['slpAmount']
                )

                for a in j
            ]


        
        query = {
                "v": 3,
                "q": {
                    "db": ["g"],
                    "aggregate": [
                    {
                        "$match": {
                        "graphTxn.outputs.address": address
                        }
                    },
                    {
                        "$unwind": "$graphTxn.outputs"
                    },
                    {
                        "$match": {
                        "graphTxn.outputs.status": "UNSPENT",
                        "graphTxn.outputs.address": address
                        }
                    },
                    {
                        "$group": {
                        "_id": "$tokenDetails.tokenIdHex",
                        "slpAmount": {
                            "$sum": "$graphTxn.outputs.slpAmount"
                        }
                        }
                    },
                    {
                        "$sort": {
                        "slpAmount": -1
                        }
                    },
                    {
                        "$match": {
                        "slpAmount": {
                            "$gt": 0
                        }
                        }
                    },
                    {
                        "$lookup": {
                        "from": "tokens",
                        "localField": "_id",
                        "foreignField": "tokenDetails.tokenIdHex",
                        "as": "token"
                        }
                    }
                    ],
                    "sort": {
                    "slpAmount": -1
                    },
                    "skip": skip,
                    "limit": limit
                }
                }


        path = cls.query_to_url(query)
        r = requests.get(url = path, timeout=DEFAULT_TIMEOUT)
        j = r.json()['g']

        return [
            
            (
            a['token'][0]['tokenDetails']['name'],
            a['slpAmount']
            )

            for a in j
        ]



    @classmethod
    def get_token_by_id(cls, tokenid):
        query = {
                "v": 3,
                "q": {
                    "db": ["t"],
                    "find": {
                    "$query": {
                        "tokenDetails.tokenIdHex": tokenid
                    }
                    },
                    "project": { "tokenDetails": 1, "tokenStats": 1, "_id": 0 },
                    "limit": 1000
                }
                }

        path = cls.query_to_url(query)
        r = requests.get(url = path, timeout=DEFAULT_TIMEOUT)
        j = r.json()['t']

        return [
            (
             a['tokenDetails']['tokenIdHex'],
             a['tokenDetails']['documentUri'],
             a['tokenDetails']['documentSha256Hex'],
             a['tokenDetails']['symbol'],
             a['tokenDetails']['name'],
             a['tokenDetails']['genesisOrMintQuantity']   
            )
            for a in j
        ]


    @classmethod
    def get_utxo_by_tokenId(cls, address, tokenId, limit=100):
        # tokenId = "7f27766677948e02aca409bf344632f3e8e350105017ef14d88fc2c048347146"
        # address = "simpleledger:qpt8z56sjcng8eux4pgvl7msnns2fzj05s89rl7w90"

        query = {
            "v": 3,
            "q": {
              "db": ["g"],
              "aggregate": [
                {
                  "$match": {
                    "graphTxn.outputs": {
                      "$elemMatch": {
                        "status": "UNSPENT",
                        "slpAmount": { "$gte": 0 }
                      }
                    },
                    "tokenDetails.tokenIdHex": tokenId
                  }
                },
                {
                  "$unwind": "$graphTxn.outputs"
                },
                {
                  "$match": {
                    "graphTxn.outputs.status": "UNSPENT",
                    "graphTxn.outputs.slpAmount": { "$gte": 0 },
                    "tokenDetails.tokenIdHex": tokenId
                  }
                },
                {
                  "$project": {
                    "token_balance": "$graphTxn.outputs.slpAmount",
                    "address": "$graphTxn.outputs.address",
                    "txid": "$graphTxn.txid",
                    "vout": "$graphTxn.outputs.vout",
                    "tokenId": "$tokenDetails.tokenIdHex"
                  }
                },
                {
                    "$match": {
                    "address": address
                    }
                }
              ],
              "limit": limit
            }
          }

        path = cls.query_to_url(query)
        r = requests.get(url = path, timeout=DEFAULT_TIMEOUT)
        j = r.json()['g']

        return [
            
            (#a['_id'],
            a['token_balance'],
            a['address'],
            a['txid'],
            a['vout']
            )

            for a in j
        ]


    @classmethod
    def get_mint_baton(cls, tokenId, limit=10):
        # tokenId = "ae885f8e1bd2a09c5f8dcf19cb9a837d8c48b370190f31841b8a4817ebdbb9d7
        query = {
            "v": 3,
            "q": {
              "db": ["g"],
              "aggregate": [
                {
                  "$match": {
                    "graphTxn.outputs": {
                      "$elemMatch": {
                        "status": "BATON_UNSPENT"
                       
                      }
                    },
                    "tokenDetails.tokenIdHex": tokenId
                  }
                  },
                  {
                  "$unwind": "$graphTxn.outputs"
                  },
                  {
                  "$match": {
                    "graphTxn.outputs.status": "BATON_UNSPENT"
                  }
                
                },
                {
                  "$project": {
                    "address": "$graphTxn.outputs.address",
                    "txid": "$graphTxn.txid",
                    "vout": "$graphTxn.outputs.vout",
                    "tokenId": "$tokenDetails.tokenIdHex"
                  }
                }
              ],
              "limit": limit
            }
        }

        path = cls.query_to_url(query)
        r = requests.get(url = path, timeout=DEFAULT_TIMEOUT)
        j = r.json()['g']

        return [
        
            (
            a['address'],
            a['txid'],
            a['vout']
            )

            for a in j
        ]