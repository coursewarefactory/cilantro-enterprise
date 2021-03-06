import requests
import pathlib
import json
import os
import sys
import time
import asyncio
import subprocess
from subprocess import call
from shutil import copyfile

import zmq.asyncio

from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError

from cilantro_ee.crypto.wallet import Wallet
from cilantro_ee.nodes.masternode.masternode import Masternode
from cilantro_ee.nodes.delegate.delegate import Delegate
from cilantro_ee.cli.utils import ask, validate_key, read_cfg

import time
from getpass import getpass


def start_mongo():
    try:
        c = MongoClient(serverSelectionTimeoutMS=200)
        c.server_info()
    except ServerSelectionTimeoutError:
        subprocess.Popen(['mongod', '--dbpath ~/blocks', '--logpath /dev/null', '--bind_ip_all'],
                         stdout=open('/dev/null', 'w'),
                         stderr=open('/dev/null', 'w'))
        print('Starting MongoDB...')
        time.sleep(3)
    except BaseException as err:
        print("Failed to start Mongo")
        print("Error: {}".format(err))


def print_ascii_art():
    print('''
                ##
              ######
            ####  ####
          ####      ####
        ####          ####
      ####              ####
        ####          ####
          ####      ####
            ####  ####
              ######
                ##

 ~ V I V A ~ L A ~ L A M D E N ! ~
''')


def clear():
    call('clear' if os.name == 'posix' else 'cls')


def is_valid_ip(s):
    components = s.split('.')
    if len(components) != 4:
        return False

    for component in components:
        if int(component) > 255:
            return False

    return True


def resolve_constitution(fp):
    path = pathlib.PosixPath(fp).expanduser()

    path.touch()

    f = open(str(path), 'r')
    j = json.load(f)
    f.close()

    assert 'masternodes' in j.keys(), 'No masternodes section.'
    assert 'masternode_min_quorum' in j.keys(), 'No masternode_min_quorum section.'
    assert 'delegates' in j.keys(), 'No delegates section.'
    assert 'delegate_min_quorum' in j.keys(), 'No delegate_min_quorum section.'

    return j


def resolve_raw_constitution(text):
    j = json.loads(text)

    assert 'masternodes' in j.keys(), 'No masternodes section.'
    assert 'masternode_min_quorum' in j.keys(), 'No masternode_min_quorum section.'
    assert 'delegates' in j.keys(), 'No delegates section.'
    assert 'delegate_min_quorum' in j.keys(), 'No delegate_min_quorum section.'

    return j


def start_node(args):
    # sleep for restart module for ppid to be killed
    time.sleep(5)

    assert args.node_type == 'masternode' or args.node_type == 'delegate', \
        'Provide node type as "masternode" or "delegate"'

    sk = bytes.fromhex(args.key)

    wallet = Wallet(seed=sk)

    bootnodes = []

    for node in args.boot_nodes:
        assert is_valid_ip(node), 'Invalid IP string provided to boot node argument.'
        bootnodes.append(f'tcp://{node}')

    assert len(bootnodes) > 0, 'Must provide at least one bootnode.'

    const = resolve_constitution(args.constitution)

    ip_str = requests.get('http://api.ipify.org').text
    socket_base = f'tcp://{ip_str}'

    # Setup Environment
    copyfile('/root/cilantro-enterprise/scripts/cil.service', '/etc/systemd/system/cil.service')


    # Enable Auto Restart
    # key, config = read_cfg()  #use restart logic to start the node again

    # if key is None or config is None:
    #     # booting for 1st time
    #     enable = ask(question='Authorize auto restart for cilantro')
    #
    #     if enable:
    #         validate_key(restart=enable, key = args.key)
    #     else:
    #         print("Auto Restart is disabled manual intervention to restart CIL")

    if args.node_type == 'masternode':
        # Start mongo
        start_mongo()

        n = Masternode(
            wallet=wallet,
            ctx=zmq.asyncio.Context(),
            socket_base=socket_base,
            bootnodes=bootnodes,
            constitution=const,
            webserver_port=args.webserver_port,
        )
    elif args.node_type == 'delegate':
        n = Delegate(
            wallet=wallet,
            ctx=zmq.asyncio.Context(),
            socket_base=socket_base,
            bootnodes=bootnodes,
            constitution=const,
        )

    loop = asyncio.get_event_loop()
    asyncio.async(n.start())
    loop.run_forever()


def setup_node():
    node_type = ''
    while node_type not in ['M', 'D']:
        node_type = input('(M)asternode or (D)elegate: ').upper()

    while True:
        sk = getpass('Signing Key in Hex Format: ')

        try:
            wallet = Wallet(seed=bytes.fromhex(sk))
            break
        except:
            print('Invalid format! Try again.')

    join_or_start = ''
    while join_or_start not in ['J', 'S']:
        join_or_start = input('(J)oin or (S)tart: ').upper()

    bootnodes = []
    mn_seed = None
    if join_or_start == 'S':
        bootnode = ''
        while len(bootnodes) < 1 or bootnode != '':
            bootnode = input('Enter bootnodes as IP string. Press Enter twice to continue: ')
            if is_valid_ip(bootnode):
                print(f'Added {bootnode}.')
                bootnodes.append(bootnode)
            elif bootnode != '':
                print(f'Invalid IP string: {bootnode}')
    else:
        while mn_seed is None:
            mn_ip = input('Enter masternode as IP string: ')
            if is_valid_ip(mn_ip):
                mn_seed = mn_ip
            else:
                print(f'Invalid IP string: {mn_seed}')

    ip_str = requests.get('http://api.ipify.org').text
    socket_base = f'tcp://{ip_str}'
    mn_seed_str = f'tcp://{mn_seed}'
    const_url = input('URL of constitution: ')
    c = requests.get(const_url)
    const = resolve_raw_constitution(c.text)

    # start_rocks()

    if node_type == 'M':
        # Start mongo
        start_mongo()

        n = Masternode(
            wallet=wallet,
            ctx=zmq.asyncio.Context(),
            socket_base=socket_base,
            bootnodes=bootnodes,
            constitution=const,
            webserver_port=18080,
            mn_seed=mn_seed_str
        )
    elif node_type == 'D':
        n = Delegate(
            wallet=wallet,
            ctx=zmq.asyncio.Context(),
            socket_base=socket_base,
            bootnodes=bootnodes,
            constitution=const,
            mn_seed=mn_seed_str
        )

    loop = asyncio.get_event_loop()
    asyncio.async(n.start())
    loop.run_forever()


def join_network(args):
    assert args.node_type == 'masternode' or args.node_type == 'delegate', \
        'Provide node type as "masternode" or "delegate"'

    sk = bytes.fromhex(args.key)

    wallet = Wallet(seed=sk)

    const = resolve_constitution(args.constitution)

    mn_seed = f'tcp://{args.mn_seed}'

    ip_str = requests.get('http://api.ipify.org').text
    socket_base = f'tcp://{ip_str}'

    # Setup Environment
    # CURR_DIR = pathlib.Path(os.getcwd())
    # os.environ['PKG_ROOT'] = str(CURR_DIR.parent)
    # os.environ['CIL_PATH'] = os.getenv('PKG_ROOT') + '/cilantro_ee'


    if args.node_type == 'masternode':
        # Start mongo
        start_mongo()

        n = Masternode(
            wallet=wallet,
            ctx=zmq.asyncio.Context(),
            socket_base=socket_base,
            constitution=const,
            webserver_port=args.webserver_port,
            mn_seed=mn_seed
        )
    elif args.node_type == 'delegate':
        start_mongo()
        n = Delegate(
            wallet=wallet,
            ctx=zmq.asyncio.Context(),
            socket_base=socket_base,
            constitution=const,
            mn_seed=mn_seed
        )

    loop = asyncio.get_event_loop()
    asyncio.async(n.start())
    loop.run_forever()
