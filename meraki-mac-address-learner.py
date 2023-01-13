import requests
import argparse
import sys
import json
import logging as log
import pandas as pd
from logging.handlers import TimedRotatingFileHandler

# -------------------------------------------------------------------
# Info
# -------------------------------------------------------------------
# Author: Cedric Metzger
# Mail: cmetzger@itris.ch / support.one@itris.ch
# Version: 1.0 / 03.01.2023
# Comment of the author: Your focus determines your reality. — Qui-Gon Jinn

# -------------------------------------------------------------------
# CONSTANTS
# -------------------------------------------------------------------

# Replace these values with your own
api_key = ""


# -------------------------------------------------------------------
# FUNCITONS
# -------------------------------------------------------------------


def updatedatabase(mac, interface, switch):
    macinterface_entry = pd.DataFrame([[mac, interface, switch]], columns=["mac", "interface", "switch"])
    log.info("checking for " + macinterface_entry['mac'] + ' ' + macinterface_entry['interface'] + ' ' + macinterface_entry['switch'])
    try:
        # try to open database
        db = pd.read_csv(args.database, sep=";", names=["mac", "interface", "switch"])
    except FileNotFoundError:
        # If the file does not exist, create it and write a header line
        with open("db.txt", "w") as file:
            file.write("mac;interface;switch\n")
        # Create an empty dataframe with the correct column names
        db = pd.DataFrame(columns=["mac", "interface", "switch"])

    # add first Entry
    log.info("DB has " + str(len(db)) + " entry/entries")
    if db.empty:
        log.info("DB empty, adding frist entry")
        db.loc[0] = [mac, interface, switch]
        # write to the database w/ headers
        db.to_csv(args.database, sep=";", index=False)
    # checking if additionals entries are already in the db
    elif not db.empty:
        log.info("checking for macinterface is in db mac")
        # only adding the entry, if there is no entry for the same mac-interface combo yet
        db = pd.merge(db, macinterface_entry, on=['mac', 'interface', 'switch'], how='outer').drop_duplicates()
        # write to the database w/o headers
        db.to_csv(args.database, sep=";", index=False, header=False)
    return 0


def getswitchports(switch, switchserial):
    headers = {
        "X-Cisco-Meraki-API-Key": api_key,
        "Content-Type": "application/json",
    }
    url = f"https://api.meraki.com/api/v1/devices/{switchserial}/clients"

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        switch_ports = response.json()
        for port in switch_ports:
            if port['mac'] is None or port['switchport'] is None:
                log.warning(switch + ": mac or switchport = none")
            else:
                log.info('switch ' + switch + ' mac ' + port['mac'] + ' switchport ' + port['switchport'])
                updatedatabase(port['mac'], port['switchport'], switch)
    else:
        log.error(f"Error: {response.status_code}")
    return 0

# -------------------------------------------------------------------
# Main
# -------------------------------------------------------------------


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="""Python script to learn mac addresses of connected ports
    Example: meraki-mac-address-learner.py -lv -t token
""")
    parser.add_argument('-f', '--file', help='file Containing switches', default='switches.txt')
    parser.add_argument('-d', '--database', help='database File', default='db.txt')
    parser.add_argument('-c', '--configure', action='store_const', help='database File', const=True)
    parser.add_argument('-l', '--learn', action='store_const', const=True, help='learn ports')
    parser.add_argument('-t', '--token', help='token', default='')

    args = parser.parse_args()
    # mandatory arguments

    # setup log
    log.basicConfig(level=log.INFO,
                    format='%(asctime)s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M',
                    stream=sys.stdout)
    log_formatter = log.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
    log_handler = TimedRotatingFileHandler(filename='meraki-mac-address-learner.log', when='midnight', interval=1,
                                           backupCount=0)
    log_handler.setFormatter(log_formatter)
    log.getLogger().addHandler(log_handler)

    if not args.file:
        log.error("Exiting. Filename is mandatory.")
        sys.exit(1)

    if args.token:
        log.info("api key: " + args.token)
        api_key = args.token

    if args.learn:
        switches = pd.read_csv(args.file, sep=";", names=["switch", "serialnumber"], header=0)
        switches.iterrows()
        for index, row in switches.iterrows():
            log.info("learning started for " + row['switch'] + ' ' + row['serialnumber'])
            getswitchports(row['switch'], row['serialnumber'])

#################################
