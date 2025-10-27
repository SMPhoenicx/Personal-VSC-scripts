#!/usr/bin/env python3
"""
Test script for RegattaNetworkScraper
Runs the scraper independently and saves results to JSON files
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Import our scraper (make sure the files are in the same directory)
from regatta_network_scraper import RegattaNetworkScraper
from base_scraper import ScraperMode

async def test_scraper():
    """Test the regatta network scraper"""
    
    # Test URL (the one you provided)
    test_url = "https://www.regattanetwork.com/clubmgmt/applet_regatta_results.php?regatta_id=30127&media_format=1"
    
    logger.info("=" * 60)
    logger.info("🏁 Testing Regatta Network Scraper")
    logger.info("=" * 60)
    logger.info(f"Test URL: {test_url}")
    logger.info("")
    
    try:
        # Create scraper instance
        logger.info("📊 Creating scraper instance...")
        scraper = RegattaNetworkScraper(mode=ScraperMode.SINGLE)
        
        # Test discovery phase
        logger.info("🔍 Testing discovery phase...")
        discovery_success = await scraper.discover(test_url)
        logger.info(f"Discovery result: {'✅ SUCCESS' if discovery_success else '❌ FAILED'}")
        
        if not discovery_success:
            logger.error("Discovery failed, cannot proceed with scraping")
            return False
        
        # Test single scrape
        logger.info("📈 Running single scrape...")
        start_time = datetime.now()
        
        results = await scraper.scrape_single(test_url)
        
        end_time = datetime.now()
        scrape_duration = (end_time - start_time).total_seconds()
        
        logger.info(f"⏱️  Scraping completed in {scrape_duration:.2f} seconds")
        
        if results:
            logger.info("✅ Scraping successful!")
            
            # Create output directory
            output_dir = Path("test_results")
            output_dir.mkdir(exist_ok=True)
            
            # Save results to JSON file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = output_dir / f"regatta_results_{timestamp}.json"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            logger.info(f"💾 Results saved to: {output_file}")
            
            # Print summary statistics
            logger.info("")
            logger.info("📊 RESULTS SUMMARY:")
            logger.info("=" * 40)
            
            event_info = results.get("event_info", {})
            divisions = results.get("divisions", [])
            
            logger.info(f"Event Title: {event_info.get('title', 'N/A')}")
            logger.info(f"Club Name: {event_info.get('club_name', 'N/A')}")
            logger.info(f"Event Dates: {event_info.get('dates', 'N/A')}")
            logger.info(f"Logo URL: {event_info.get('logo_url', 'N/A')}")
            logger.info("")
            logger.info(f"Total Divisions: {len(divisions)}")
            
            total_boats = 0
            for i, division in enumerate(divisions, 1):
                boat_count = division.get("boat_count", 0)
                results_count = len(division.get("results", []))
                total_boats += boat_count
                
                logger.info(f"  Division {i}: {division.get('name', 'Unknown')}")
                logger.info(f"    - Boats: {boat_count}")
                logger.info(f"    - Results: {results_count}")
                logger.info(f"    - Races Scored: {division.get('races_scored', 'N/A')}")
                logger.info(f"    - Last Updated: {division.get('last_updated', 'N/A')}")
                
                # Show first few results as examples
                results_list = division.get("results", [])
                if results_list:
                    logger.info(f"    - Sample Results:")
                    for j, result in enumerate(results_list[:3]):  # Show first 3
                        pos = result.get("position", "?")
                        sail = result.get("sail_number", "?")
                        boat = result.get("boat_name", "?")
                        skipper = result.get("skipper", "?")
                        points = result.get("total_points", "?")
                        logger.info(f"      {pos}. #{sail} {boat} ({skipper}) - {points} pts")
                    
                    if len(results_list) > 3:
                        logger.info(f"      ... and {len(results_list) - 3} more")
                
                logger.info("")
            
            logger.info(f"Total Boats Across All Divisions: {total_boats}")
            logger.info("")
            
            # Create a human-readable summary file
            summary_file = output_dir / f"regatta_summary_{timestamp}.txt"
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write("REGATTA NETWORK SCRAPER TEST RESULTS\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Source URL: {test_url}\n")
                f.write(f"Scraping Duration: {scrape_duration:.2f} seconds\n\n")
                
                f.write("EVENT INFORMATION:\n")
                f.write("-" * 20 + "\n")
                f.write(f"Title: {event_info.get('title', 'N/A')}\n")
                f.write(f"Club: {event_info.get('club_name', 'N/A')}\n")
                f.write(f"Dates: {event_info.get('dates', 'N/A')}\n")
                f.write(f"Logo: {event_info.get('logo_url', 'N/A')}\n\n")
                
                f.write("DIVISIONS:\n")
                f.write("-" * 20 + "\n")
                for i, division in enumerate(divisions, 1):
                    f.write(f"\n{i}. {division.get('name', 'Unknown Division')}\n")
                    f.write(f"   Boats: {division.get('boat_count', 0)}\n")
                    f.write(f"   Races Scored: {division.get('races_scored', 'N/A')}\n")
                    f.write(f"   Last Updated: {division.get('last_updated', 'N/A')}\n")
                    f.write(f"   Results Count: {len(division.get('results', []))}\n")
                    
                    # Write all results for this division
                    results_list = division.get("results", [])
                    if results_list:
                        f.write(f"   \n   RESULTS:\n")
                        f.write(f"   Pos | Sail   | Boat Name        | Skipper           | Race Results | Points\n")
                        f.write(f"   ----+--------+------------------+-------------------+--------------+-------\n")
                        
                        for result in results_list:
                            pos = str(result.get("position", "?")).ljust(3)
                            sail = str(result.get("sail_number", "?")).ljust(6)
                            boat = str(result.get("boat_name", "?"))[:16].ljust(16)
                            skipper = str(result.get("skipper", "?"))[:17].ljust(17)
                            race_results = str(result.get("race_results", "?"))[:12].ljust(12)
                            points = str(result.get("total_points", "?")).ljust(5)
                            
                            f.write(f"   {pos} | {sail} | {boat} | {skipper} | {race_results} | {points}\n")
            
            logger.info(f"📄 Human-readable summary saved to: {summary_file}")
            logger.info("")
            logger.info("🎉 Test completed successfully!")
            return True
            
        else:
            logger.error("❌ Scraping failed - no results returned")
            return False
            
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

async def test_with_multiple_urls():
    """Test with multiple URLs if you want to test different regattas"""
    urls = [
        "https://www.regattanetwork.com/clubmgmt/applet_regatta_results.php?regatta_id=29824&&&&&&&&media_format=1",
        # Add more URLs here if you want to test multiple regattas
    ]
    
    logger.info(f"🧪 Testing {len(urls)} URL(s)")
    
    success_count = 0
    for i, url in enumerate(urls, 1):
        logger.info(f"\n{'='*20} TEST {i}/{len(urls)} {'='*20}")
        success = await test_scraper_url(url, i)
        if success:
            success_count += 1
    
    logger.info(f"\n🏁 FINAL RESULTS: {success_count}/{len(urls)} tests passed")

async def test_scraper_url(url: str, test_num: int) -> bool:
    """Test a single URL"""
    try:
        scraper = RegattaNetworkScraper(mode=ScraperMode.SINGLE)
        results = await scraper.scrape_single(url)
        
        if results:
            # Save results
            output_dir = Path("test_results")
            output_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = output_dir / f"regatta_results_test{test_num}_{timestamp}.json"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Test {test_num} successful - saved to {output_file}")
            return True
        else:
            logger.error(f"❌ Test {test_num} failed - no results")
            return False
            
    except Exception as e:
        logger.error(f"❌ Test {test_num} failed: {e}")
        return False

if __name__ == "__main__":
    logger.info("Starting Regatta Network Scraper Test")
    
    # Run the test
    try:
        result = asyncio.run(test_scraper())
        if result:
            logger.info("\n✅ All tests passed!")
            sys.exit(0)
        else:
            logger.error("\n❌ Tests failed!")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("\n⏹️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n💥 Unexpected error: {e}")
        sys.exit(1)