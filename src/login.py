import asyncio
import os
from browser_use_sdk.v3 import AsyncBrowserUse

async def main():
    client = AsyncBrowserUse()
    
    # 1. We use the exact Profile ID that was generated for your LinkedIn session
    # This will KEEP your LinkedIn cookies and just add Glassdoor cookies to the same profile!
    profile_id = "1c9c2845-8083-4d15-9c66-9f73f09affe2"
    
    # 2. Attach that existing profile to a new session
    session = await client.sessions.create(profile_id=profile_id)
    
    # 3. Get the URL so you can log in manually
    print("\n==============================================")
    print("Click this link to open the Live View:")
    print(session.live_url)
    print("==============================================\n")
    
    print("Booting up the cloud browser and going to Glassdoor...")
    # 4. Force cloud browser to open Glassdoor
    await client.run("Go to glassdoor.com and simply wait.", session_id=session.id)
    
    # 5. Pause the script while you log in 
    input("The browser is now ready! Go to the live view, log into Glassdoor, then press Enter here once you are done...")

    # 6. Stop the session to merge the new cookies
    await client.sessions.stop(session.id)
    
    print("\nSuccess! Your Glassdoor cookies are now saved to profile:", profile_id)
    print("This profile now has BOTH your LinkedIn and Glassdoor cookies safely stored.")

if __name__ == "__main__":
    asyncio.run(main())
