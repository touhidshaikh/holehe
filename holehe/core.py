from bs4 import BeautifulSoup
from termcolor import colored
import httpx
import trio

from subprocess import Popen, PIPE
import os
from argparse import ArgumentParser
import csv
from datetime import datetime
import time
import importlib
import pkgutil
import hashlib
import re
import sys
import string
import random
import json

from holehe.localuseragent import ua
from holehe.instruments import TrioProgress


try:
    import cookielib
except Exception:
    import http.cookiejar as cookielib


DEBUG        = False
EMAIL_FORMAT = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'

__version__ = "1.61"


def import_submodules(package, recursive=True):
    """Get all the holehe submodules"""
    if isinstance(package, str):
        package = importlib.import_module(package)
    results = {}
    for loader, name, is_pkg in pkgutil.walk_packages(package.__path__):
        full_name = package.__name__ + '.' + name
        results[full_name] = importlib.import_module(full_name)
        if recursive and is_pkg:
            results.update(import_submodules(full_name))
    return results


def get_functions(modules, args=None):
    """Transform the modules objects to functions"""
    websites = []

    for module in modules:
        if len(module.split(".")) > 3 :
            modu = modules[module]
            site = module.split(".")[-1]
            if args is not None and args.nopasswordrecovery:
                if  "adobe" not in str(modu.__dict__[site]) and "mail_ru" not in str(modu.__dict__[site]) and "odnoklassniki" not in str(modu.__dict__[site]) and "samsung" not in str(modu.__dict__[site]):
                    websites.append(modu.__dict__[site])
            else:
                websites.append(modu.__dict__[site])
    return websites

def check_update():
    """Check and update holehe if not the last version"""
    check_version = httpx.get("https://pypi.org/pypi/holehe/json")
    if check_version.json()["info"]["version"] != __version__:
        if os.name != 'nt':
            p = Popen(["pip3",
                       "install",
                       "--upgrade",
                       "holehe"],
                      stdout=PIPE,
                      stderr=PIPE)
        else:
            p = Popen(["pip",
                       "install",
                       "--upgrade",
                       "holehe"],
                      stdout=PIPE,
                      stderr=PIPE)
        (output, err) = p.communicate()
        p_status = p.wait()
        print("Holehe has just been updated, you can restart it.")
        exit()

def credit():
    """Print Credit"""
    print('Twitter : @palenath')
    print('Github : https://github.com/megadose/holehe')
    print('For BTC Donations : 1FHDM49QfZX6pJmhjLE5tB2K6CaTLMZpXZ')

def is_email(email: str) -> bool:
    """Check if the input is a valid email address

    Keyword Arguments:
    email       -- String to be tested

    Return Value:
    Boolean     -- True if string is an email, False otherwise
    """

    return bool(re.fullmatch(EMAIL_FORMAT, email))

def print_result(data, args, email, start_time, websites):
    def print_color(text, color, args):
        if not args.nocolor:
            return colored(text, color)
        else:
            return text

    if args.jsonoutput:
        print(json.dumps(data, indent=4))
        return

    description = print_color("[+] Email used", "green", args) + "," + print_color(" [-] Email not used", "magenta", args) + "," + print_color(" [x] Rate limit", "yellow", args) + "," + print_color(" [!] Error", "red", args)
    if not args.noclear:
        print("\033[H\033[J")
    else:
        print("\n")
    print("*" * (len(email) + 6))
    print("   " + email)
    print("*" * (len(email) + 6))

    for results in data:
        if results["rateLimit"] and not args.onlyused:
            websiteprint = print_color("[x] " + results["domain"], "yellow", args)
            print(websiteprint)
        elif "error" in results.keys() and results["error"] and not args.onlyused:
            toprint = ""
            if results["others"] is not None and "Message" in str(results["others"].keys()):
                toprint = " Error message: " + results["others"]["errorMessage"]
            websiteprint = print_color("[!] " + results["domain"] + toprint, "red", args)
            print(websiteprint) 
        elif not results["exists"] and not args.onlyused:
            websiteprint = print_color("[-] " + results["domain"], "magenta", args)
            print(websiteprint)
        elif results["exists"]:
            toprint = ""
            if results["emailrecovery"] is not None:
                toprint += " " + results["emailrecovery"]
            if results["phoneNumber"] is not None:
                toprint += " / " + results["phoneNumber"]
            if results["others"] is not None and "FullName" in str(results["others"].keys()):
                toprint += " / FullName " + results["others"]["FullName"]
            if results["others"] is not None and "Date, time of the creation" in str(results["others"].keys()):
                toprint += " / Date, time of the creation " + results["others"]["Date, time of the creation"]

            websiteprint = print_color("[+] " + results["domain"] + toprint, "green", args)
            print(websiteprint)

    print("\n" + description)
    print(str(len(websites)) + " websites checked in " +
          str(round(time.time() - start_time, 2)) + " seconds")

def export_csv(data, args, email):
    """Export result to csv"""
    if args.csvoutput:
        now = datetime.now()
        timestamp = datetime.timestamp(now)
        name_file="holehe_"+str(round(timestamp))+"_"+email+"_results.csv"
        with open(name_file, 'w', encoding='utf8', newline='') as output_file:
            fc = csv.DictWriter(output_file, fieldnames=data[0].keys())
            fc.writeheader()
            fc.writerows(data)
        exit("All results have been exported to "+name_file)

async def launch_module(module, email, client, out):
    data = {'aboutme': 'about.me', 'adobe': 'adobe.com', 'amazon': 'amazon.com', 'anydo': 'any.do', 'archive': 'archive.org', 'armurerieauxerre': 'armurerie-auxerre.com', 'atlassian': 'atlassian.com', 'babeshows': 'babeshows.co.uk', 'badeggsonline': 'badeggsonline.com', 'biosmods': 'bios-mods.com', 'biotechnologyforums': 'biotechnologyforums.com', 'bitmoji': 'bitmoji.com', 'blablacar': 'blablacar.com', 'blackworldforum': 'blackworldforum.com', 'blip': 'blip.fm', 'blitzortung': 'forum.blitzortung.org', 'bluegrassrivals': 'bluegrassrivals.com', 'bodybuilding': 'bodybuilding.com', 'buymeacoffee': 'buymeacoffee.com', 'cambridgemt': 'discussion.cambridge-mt.com', 'caringbridge': 'caringbridge.org', 'chinaphonearena': 'chinaphonearena.com', 'clashfarmer': 'clashfarmer.com', 'codecademy': 'codecademy.com', 'codeigniter': 'forum.codeigniter.com', 'codepen': 'codepen.io', 'coroflot': 'coroflot.com', 'cpaelites': 'cpaelites.com', 'cpahero': 'cpahero.com', 'cracked_to': 'cracked.to', 'crevado': 'crevado.com', 'deliveroo': 'deliveroo.com', 'demonforums': 'demonforums.net', 'devrant': 'devrant.com', 'diigo': 'diigo.com', 'discord': 'discord.com', 'docker': 'docker.com', 'dominosfr': 'dominos.fr', 'ebay': 'ebay.com', 'ello': 'ello.co', 'envato': 'envato.com', 'eventbrite': 'eventbrite.com', 'evernote': 'evernote.com', 'fanpop': 'fanpop.com', 'firefox': 'firefox.com', 'flickr': 'flickr.com', 'freelancer': 'freelancer.com', 'freiberg': 'drachenhort.user.stunet.tu-freiberg.de', 'frontiersin': 'frontiersin.org', 'g2a': 'g2a.com', 'gamespot': 'gamespot.com', 'gamevicio': 'gamevicio.com', 'gearbest': 'gearbest.com', 'genius': 'genius.com', 'git': 'git.com', 'github': 'github.com', 'goodreads': 'goodreads.com', 'gravatar': 'gravatar.com', 'hackforums': 'hackforums.net', 'hackerone': 'hackerone.com', 'hardmob': 'hardmob.com.br', 'hattrick': 'hattrick.org', 'houseparty': 'houseparty.com', 'hubpages': 'hubpages.com', 'hubspot': 'hubspot.com', 'hulu': 'hulu.com', 'ifood': 'ifood.com.br', 'ifunny': 'ifunny.co', 'imdb': 'imdb.com', 'instructables': 'instructables.com', 'intel': 'intel.com', 'italki': 'italki.com', 'jodel': 'jodel.com', 'jsfiddle': 'jsfiddle.net', 'kaggle': 'kaggle.com', 'keybase': 'keybase.io', 'kontentmachine': 'kontentmachine.com', 'lastfm': 'last.fm', 'latex': 'latex.org', 'leagueoflegends': 'leagueoflegends.com', 'legalrc': 'legalrc.biz', 'libgen': 'libgen.is', 'lichess': 'lichess.org', 'linkedin': 'linkedin.com', 'lolzteam': 'lolz.team', 'lyft': 'lyft.com', 'mcmagyar': 'mcmagyar.hu', 'medium': 'medium.com', 'meetup': 'meetup.com', 'minecraft': 'minecraft.net', 'monday': 'monday.com', 'myanimelist': 'myanimelist.net', 'neopets': 'neopets.com', 'newgrounds': 'newgrounds.com', 'nike': 'nike.com', 'nvidia': 'nvidia.com', 'ok': 'ok.ru', 'openfoodfacts': 'openfoodfacts.org', 'orkut': 'orkut.com', 'overclock': 'overclock.net', 'pinterest': 'pinterest.com', 'pokemonshowdown': 'pokemonshowdown.com', 'pornhub': 'pornhub.com', 'prezi': 'prezi.com', 'psn': 'psn.com', 'ravelry': 'ravelry.com', 'redtube': 'redtube.com', 'repl': 'repl.it', 'researchgate': 'researchgate.net', 'roblox': 'roblox.com', 'runescape': 'runescape.com', 'rutube': 'rutube.ru', 'signal': 'signal.org', 'skillshare': 'skillshare.com', 'slashdot': 'slashdot.org', 'slideshare': 'slideshare.net', 'smule': 'smule.com', 'snapchat': 'snapchat.com', 'soundcloud': 'soundcloud.com', 'spotify': 'spotify.com', 'stackexchange': 'stackexchange.com', 'steam': 'steam.com', 'subito': 'subito.it', 'taringa': 'taringa.net', 'telegram': 'telegram.org', 'tripadvisor': 'tripadvisor.com', 'twitch': 'twitch.com', 'twitter': 'twitter.com', 'uber': 'uber.com', 'uberpeople': 'uberpeople.com', 'ulule': 'ulule.com', 'usbank': 'usbank.com', 'venmo': 'venmo.com', 'vk': 'vk.com', 'vsco': 'vsco.co', 'wattpad': 'wattpad.com', 'wayn': 'wayn.com', 'whatsapp': 'whatsapp.com', 'xing': 'xing.com', 'yahoo': 'yahoo.com', 'yandex': 'yandex.ru', 'youporn': 'youporn.com', 'zoom_us': 'zoom.us', 'zotero': 'zotero.org', 'zynga': 'zynga.com'}
    result = {"domain": data[module.__name__.split(".")[-1]], "exists": False, "rateLimit": False, "emailrecovery": None, "phoneNumber": None, "others": None, "error": False}
    try:
        output = await module.check(email, client)
        if output["rateLimit"]:
            result["rateLimit"] = True
        elif output["exists"]:
            result["exists"] = True
            if "emailrecovery" in output.keys():
                result["emailrecovery"] = output["emailrecovery"]
            if "phoneNumber" in output.keys():
                result["phoneNumber"] = output["phoneNumber"]
            if "others" in output.keys():
                result["others"] = output["others"]
    except Exception as e:
        result["error"] = True
        result["others"] = str(e)
        if DEBUG:
            raise e

    out.append(result)


async def maincore(args):
    start_time = time.time()
    if not args.nocredit:
        credit()

    if not is_email(args.email):
        exit("Email badly formated")
    email = args.email

    if not args.noupdate:
        check_update()

    modules = import_submodules("holehe.modules")
    websites = get_functions(modules, args)
    if args.output:
        csv_file = args.output
    else:
        csv_file = "holehe.csv"

    headers = {
        "User-Agent": ua.random,
        "Connection": "close"
    }

    async with httpx.AsyncClient(headers=headers, timeout=args.timeout) as client:
        limit = trio.CapacityLimiter(10)
        progress = TrioProgress(len(websites), 'Checking email')

        async def worker(module, out):
            async with limit:
                async with progress:
                    await launch_module(module, email, client, out)

        out = []
        async with trio.open_nursery() as nursery:
            for module in websites:
                nursery.start_soon(worker, module, out)

    out = sorted(out, key=lambda x: x["exists"], reverse=True)
    print_result(out, args, email, start_time, websites)
    export_csv(out, args, email)


def main():
    parser = ArgumentParser(description="Holehe checks if an email is registered on various websites.")
    parser.add_argument("email", help="Email address to check")
    parser.add_argument("--noupdate", help="Do not check for update", action="store_true")
    parser.add_argument("--nocolor", help="Disable colored output", action="store_true")
    parser.add_argument("--nocredit", help="Disable credits display", action="store_true")
    parser.add_argument("--noclear", help="Disable screen clearing before output", action="store_true")
    parser.add_argument("--csvoutput", help="Export results to CSV", action="store_true")
    parser.add_argument("--timeout", help="Set timeout for HTTP requests", type=int, default=20)
    parser.add_argument("--nopasswordrecovery", help="Disable password recovery services checks", action="store_true")
    parser.add_argument("--onlyused", help="Only display results with used emails", action="store_true")
    parser.add_argument("--jsonoutput", help="Output results in JSON format", action="store_true")
    args = parser.parse_args()

    trio.run(maincore, args)


if __name__ == '__main__':
    main()
