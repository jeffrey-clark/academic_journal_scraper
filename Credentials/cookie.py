
'''
How to update the cookies:
    1. visit this link:
        https://academic-oup-com.ez.hhs.se/ej/issue/124/577
        https://academic-oup-com.ludwig.lub.lu.se/ej/issue/124/577
    2. login with your hhs/lu credentials
    3. open chrome developer tools > Network
    4. refresh the link in step 1
    5. Look for the resource 557 (the main page). Right click it and copy as cURL (Bash)
    6. Paste the copied cURL into https://curlconverter.com/ (https://curl.trillworks.com/)
    7. Copy the formatted cookies variable and replace below

    Happy Scraping!
'''


university = "LU"   # ["SSE", "LU"]

cookies = {
    'oup-cookie': '',
    'ezproxy': '',
    'JSESSIONID': '',
}

