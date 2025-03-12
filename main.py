from eth_account import Account
from eth_account.messages import encode_defunct
from utils.utils import error_handler, check_proxy, get_proxy, sleep, decimalToInt
from utils.constants import DEFAULT_KEYS
import requests
from fake_useragent import UserAgent
import json
import questionary
from loguru import logger
import sys
from eth_account import Account

logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> |  <level>{message}</level>",
    colorize=True
)
class Checker(): 

    def __init__(self,private_key:str, proxy:dict = None): 

        self.account = Account.from_key(private_key)
        self.address = self.account.address
        self.proxy = proxy 
        self.base_url = f'https://claim.elixir.xyz/backend/wallet/'
        self.headers = {
            'accept':'*/*',
            'accept-encoding':'gzip, deflate, br, zstd',
            'accept-language':'en-US;q=0.8,en;q=0.7',
            'referer': 'https://claim.elixir.xyz/',
            'user-agent': UserAgent().random
        }

    def authenticate(self,): 

        msg = f"""Welcome to Elixir Airdrop!\r\nAddress: {self.address}"""
        signed_msg = self.account.sign_message(encode_defunct(text=msg))
        signature = '0x'+ signed_msg.signature.hex()

        url = self.base_url + 'login'
        response = requests.post(
            url, 
            json={'address':self.address, 'chainId': 1, 'signature':signature}, 
            proxies=self.proxy, 
            headers=self.headers
        )
        
        if response.status_code != 201: 
            raise Exception(f'Error authenticating: {response.status_code} - {response.content}')   
        
        return response.json()['jwtToken']
    
    @error_handler('getting amount')
    def get_amount(self, ): 

        jwt = self.authenticate()
        self.headers['Clq-Jwt'] = jwt
        self.headers['Clq-App-Id'] = ''

        response = requests.get(self.base_url+f'eligibility?address={self.address}', proxies=self.proxy, headers=self.headers)

        if response.status_code == 403: 
            raise Exception(f'Forbidden - probably proxy {self.proxy["http"]} is banned')

        if response.status_code != 304 and response.status_code != 200:
            raise Exception(f'Error getting amount: {response.status_code} - {response.content}')
        
        eligible = response.json()['eligibility']
        if not eligible:
            logger.error(f'{self.address} is not eligible')
            return 0

        amount_min = float(response.json()['tokenAmountRange']['amountStart'])
        amount_max = float(response.json()['tokenAmountRange']['amountEnd'])
        logger.info(f'{self.address}: min amount received: {amount_min}')
        logger.info(f'{self.address}: max amount received: {amount_max}')
        return [amount_min, amount_max]

def main(): 

    check_proxy()

    with open(DEFAULT_KEYS, 'r', encoding='utf-8') as f: 
        keys = f.read().splitlines()

    total_min_amount = 0
    total_max_amount = 0
    for key in keys: 
        proxy = get_proxy(key)
        checker = Checker(key, proxy)
        amount = checker.get_amount()
        if amount == 0:
            continue
        else: 
            total_min_amount += amount[0]
            total_max_amount += amount[1]

    logger.success(f'Total minimum amount to claim: {total_min_amount}')
    logger.success(f'Total maximum amount to claim: {total_max_amount}')


if __name__ == '__main__': 
    main()
