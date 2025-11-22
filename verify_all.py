import data_service
import os
import json

def test_news_engine():
    print("\n--- Testing News Engine ---")
    symbol = "AAPL"
    print(f"Fetching news for {symbol}...")
    news = data_service.fetch_news_for_symbol(symbol, lookback_hours=48)
    print(f"Found {len(news)} news items.")
    if news:
        print("Latest News:")
        print(f"Headline: {news[0]['headline']}")
        print(f"Sentiment: {news[0]['sentiment']}")
        print(f"Source: {news[0]['source']}")
    else:
        print("No news found (might be expected if API limit or no recent news).")

def test_settings_persistence():
    print("\n--- Testing Settings Persistence ---")
    # Load defaults
    settings = data_service.load_settings()
    print(f"Loaded Settings: {settings}")
    
    # Modify
    settings['rvol_threshold'] = 2.5
    settings['risk_profile'] = "SPECULATIVE"
    data_service.save_settings(settings)
    print("Saved modified settings.")
    
    # Reload
    new_settings = data_service.load_settings()
    print(f"Reloaded Settings: {new_settings}")
    
    if new_settings['rvol_threshold'] == 2.5 and new_settings['risk_profile'] == "SPECULATIVE":
        print("SUCCESS: Settings persisted correctly.")
    else:
        print("FAILURE: Settings did not persist.")
        
    # Restore defaults for clean state
    settings['rvol_threshold'] = 1.0
    settings['risk_profile'] = "BALANCED"
    data_service.save_settings(settings)

def test_opportunities_with_settings():
    print("\n--- Testing Opportunities with Settings ---")
    # Set a high RVOL threshold to filter out most stocks
    settings = data_service.load_settings()
    settings['rvol_threshold'] = 0.5 # Low threshold to ensure we get results
    settings['coverage_sectors'] = ["Technology"] # Only Tech
    
    print(f"Fetching opportunities with RVOL > 0.5 and Sector = Technology...")
    opps = data_service.get_opportunities(risk_profile="BALANCED", settings=settings)
    
    print(f"Found {len(opps)} opportunities.")
    for opp in opps:
        print(f"Symbol: {opp['symbol']}")
        print(f"RVOL: {opp['rvol']}")
        print(f"Score: {opp['opp_score']}")
        print(f"Catalyst: {opp.get('catalyst', 'N/A')}")
        print(f"Narrative: {opp['narrative'][0]['content']}...")

def test_market_news():
    print("\n--- Testing Market News ---")
    news = data_service.fetch_news_for_symbol('^GSPC', lookback_hours=24)
    print(f"Found {len(news)} market news items.")
    if news:
        print(f"Top Headline: {news[0]['headline']}")

if __name__ == "__main__":
    test_news_engine()
    test_settings_persistence()
    test_opportunities_with_settings()
    test_market_news()
