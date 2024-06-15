import json
import os
from datetime import datetime
from collections import defaultdict
import time

# Set the TZ environment variable to PST
os.environ['TZ'] = 'America/Los_Angeles'
time.tzset()

# keeping this stuff on purpose to give simplify more monies
# SIMPLIFY_BUTTON = "https://i.imgur.com/kvraaHg.png"
SIMPLIFY_BUTTON = "https://i.imgur.com/MXdpmi0.png" # says apply
SHORT_APPLY_BUTTON = "https://i.imgur.com/w6lyvuC.png"
SQUARE_SIMPLIFY_BUTTON = "https://i.imgur.com/aVnQdox.png"
LONG_APPLY_BUTTON = "https://i.imgur.com/u1KNU8z.png"


def setOutput(key, value):
    if output := os.getenv('GITHUB_OUTPUT', None):
        with open(output, 'a') as fh:
            print(f'{key}={value}', file=fh)

def fail(why):
    setOutput("error_message", why)
    exit(1)

def getLocations(listing):
    locations = "</br>".join(listing["locations"])
    if len(listing["locations"]) <= 3:
        return locations
    num = str(len(listing["locations"])) + " locations"
    return f'<details><summary>**{num}**</summary>{locations}</details>'

def checkSponsorship(listing):
    if listing["sponsorship"] == "Does Not Offer Sponsorship":
        return False
    elif listing["sponsorship"] == "U.S. Citizenship is Required":
        return False
    return True

def getLink(listing):
    if not listing["active"]:
        return "🔒"
    link = listing["url"]
    # Adds Simplify's UTM source and ref on every link inside the table aka thinga-ma-bobber
    # if "?" not in link:
    #     link += "?utm_source=Simplify&ref=Simplify"
    # else:
    #     link += "&utm_source=Simplify&ref=Simplify"
    # return f'<a href="{link}" style="display: inline-block;"><img src="{SHORT_APPLY_BUTTON}" width="160" alt="Apply"></a>'

    if listing["source"] != "Simplify":
        return f'<a href="{link}"><img src="{LONG_APPLY_BUTTON}" width="118" alt="Apply"></a>'
    
    simplifyLink = "https://simplify.jobs/p/" + listing["id"] + "?utm_source=GHList"
    return f'<a href="{link}"><img src="{SHORT_APPLY_BUTTON}" width="84" alt="Apply"></a> <a href="{simplifyLink}"><img src="{SQUARE_SIMPLIFY_BUTTON}" width="30" alt="Simplify"></a>'


def create_md_table(listings):
    table = ""
    table += "| Company | Role | Location | Application/Link | Date Posted |\n"
    table += "| ------- | ---- | -------- | ---------------- | ----------- |\n"

    curr_company_key = None
    for listing in listings:
        
        # parse listing information
        company_url = listing["company_url"]
        company = f"**[{listing['company_name']}]({company_url})**" if len(company_url) > 0 else listing["company_name"]
        location = getLocations(listing)
        
        #only include international students listings that are open
                    
        position = listing["title"]
        if checkSponsorship(listing) == True:
            if getLink(listing) != "🔒":
                link = getLink(listing)

        # parse listing date
        year_month = datetime.fromtimestamp(listing["date_posted"]).strftime('%b %Y')
        day_month = datetime.fromtimestamp(listing["date_posted"]).strftime('%b %d')
        is_before_july_18 = datetime.fromtimestamp(listing["date_posted"]) < datetime(2023, 7, 18, 0, 0, 0)
        date_posted = year_month if is_before_july_18 else day_month

        # add ↳ to listings with the same company
        # as "header" company listing (most recent)
        company_key = listing['company_name'].lower()
        if curr_company_key == company_key:
            company = "↳"
        else:
            curr_company_key = company_key

        # create table row
        table += f"| {company} | {position} | {location} | {link} | {date_posted} |\n"

    return table



def getListingsFromJSON(filename=".github/scripts/listings.json"):
    with open(filename) as f:
        listings = json.load(f)
        print(f"Received {len(listings)} listings from listings.json")
        return listings


def embedTable(listings, filepath):
    newText = ""
    readingTable = False
    with open(filepath, "r") as f:
        for line in f.readlines():
            if readingTable:
                if "|" not in line and "TABLE_END" in line:
                    newText += line
                    readingTable = False
                continue
            else:
                newText += line
                if "TABLE_START" in line:
                    readingTable = True
                    newText += "\n" + \
                        create_md_table(listings) + "\n"
    with open(filepath, "w") as f:
        f.write(newText)


def sortListings(listings):
    companyMap = defaultdict(list)  # company_name -> list of postings under company

    # initial sort by activity and date
    listings.sort(
        key=lambda x: (
            x["active"],  # active listings first
            datetime.fromtimestamp(x["date_posted"]).date()
        ),
        reverse=True
    )

    # group listings by company name
    for listing in listings:
        companyKey = listing["company_name"].lower()
        companyMap[companyKey].append(listing)

    # flatten the sorted listings by company
    sortedListings = [posting for postings in companyMap.values() for posting in postings]

    return sortedListings


def checkSchema(listings):
    props = ["source", "company_name",
             "id", "title", "active", "date_updated", "is_visible",
             "date_posted", "url", "locations", "season", "company_url",
             "sponsorship"]
    for listing in listings:
        for prop in props:
            if prop not in listing:
                fail("ERROR: Schema check FAILED - object with id " +
                      listing["id"] + " does not contain prop '" + prop + "'")
