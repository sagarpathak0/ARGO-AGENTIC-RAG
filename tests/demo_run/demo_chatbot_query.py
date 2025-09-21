#!/usr/bin/env python3
"""
Demo: How the AI chatbot would retrieve salinity data for Indonesian waters in 1999
"""

import pandas as pd
import glob
from pathlib import Path
import json

def demo_salinity_query():
    """Simulate the AI chatbot's response to salinity query"""
    
    # Step 1: Read metadata CSV (what the chatbot would query from PostgreSQL)
    metadata_file = Path("gadr/data/indian/processed_profiles/profiles_metadata.csv")
    
    if not metadata_file.exists():
        print("❌ Metadata file not found. Run the ingestion script first.")
        return
    
    df = pd.read_csv(metadata_file)
    
    # Step 2: Filter for Indonesian waters in 1999 (what SQL would return)
    indonesian_profiles = df[
        (df['latitude'] >= -15) & (df['latitude'] <= -5) &  # Indonesian latitudes
        (df['longitude'] >= 95) & (df['longitude'] <= 140) &  # Indonesian longitudes  
        (df['time_coverage_start'].str.startswith('1999')) &  # Year 1999
        (df['keywords'].str.contains('salinity', na=False))   # Has salinity data
    ]
    
    print("🤖 AI Chatbot Response:")
    print("=" * 50)
    print(f"📊 Found {len(indonesian_profiles)} profiles matching your query")
    print(f"📍 Location: Indonesian waters (Indian Ocean)")
    print(f"📅 Time: 1999")
    print(f"🏛️ Institution: {indonesian_profiles['institution'].iloc[0] if len(indonesian_profiles) > 0 else 'N/A'}")
    
    if len(indonesian_profiles) == 0:
        print("❌ No profiles found in Indonesian coastal waters for 1999")
        return
    
    # Step 3: Analyze profile locations and times
    print(f"\n📍 Geographic Coverage:")
    print(f"   Latitude range: {indonesian_profiles['latitude'].min():.3f}° to {indonesian_profiles['latitude'].max():.3f}°S")
    print(f"   Longitude range: {indonesian_profiles['longitude'].min():.3f}° to {indonesian_profiles['longitude'].max():.3f}°E")
    print(f"   Depth range: {indonesian_profiles['depth_min'].min():.1f} to {indonesian_profiles['depth_max'].max():.1f} meters")
    
    # Step 4: Time series information
    print(f"\n⏰ Temporal Coverage:")
    earliest = indonesian_profiles['time_coverage_start'].min()
    latest = indonesian_profiles['time_coverage_start'].max()
    print(f"   Period: {earliest} to {latest}")
    
    # Step 5: Sample a few profiles to show salinity data
    print(f"\n🌊 Sample Salinity Profiles:")
    
    sample_profiles = indonesian_profiles.head(3)  # Take first 3 profiles
    
    for idx, profile in sample_profiles.iterrows():
        print(f"\n📋 Profile {profile['profile_id'][:8]}...")
        print(f"   📍 Location: {profile['latitude']:.3f}°S, {profile['longitude']:.3f}°E") 
        print(f"   📅 Date: {profile['time_coverage_start']}")
        print(f"   🏔️ Depth: {profile['depth_min']:.1f} - {profile['depth_max']:.1f}m")
        
        # Parse QC summary
        try:
            qc_data = json.loads(profile['qc_summary'])
            psal_quality = qc_data.get('psal_bad_frac', 0) * 100
            print(f"   ✅ Salinity data quality: {100-psal_quality:.1f}% good")
        except:
            print(f"   ⚠️ Quality data unavailable")
        
        # Try to read actual salinity data from Parquet file
        parquet_path = Path(profile['parquet_path'])
        if parquet_path.exists():
            try:
                profile_data = pd.read_parquet(parquet_path)
                if 'psal' in profile_data.columns:
                    salinity = profile_data['psal'].dropna()
                    if len(salinity) > 0:
                        print(f"   🧂 Salinity range: {salinity.min():.2f} - {salinity.max():.2f} PSU")
                        print(f"   📊 Measurements: {len(salinity)} depth levels")
                        # Show surface and deep values
                        if len(salinity) >= 2:
                            print(f"   🌊 Surface salinity (~{profile_data['pres'].min():.0f}m): {salinity.iloc[0]:.2f} PSU")
                            print(f"   🏔️ Deep salinity (~{profile_data['pres'].max():.0f}m): {salinity.iloc[-1]:.2f} PSU")
                else:
                    print(f"   ❌ No salinity data in parquet file")
            except Exception as e:
                print(f"   ⚠️ Could not read salinity data: {e}")
        else:
            print(f"   ❌ Parquet file not found: {parquet_path}")
    
    # Step 6: Summary and insights
    print(f"\n🔍 Key Insights:")
    print(f"   • This represents Argo float 0042682's journey through Indonesian waters")
    print(f"   • Data covers {(pd.to_datetime(latest) - pd.to_datetime(earliest)).days} days of observations")
    print(f"   • Measurements span from shallow ({indonesian_profiles['depth_min'].min():.0f}m) to deep ocean ({indonesian_profiles['depth_max'].max():.0f}m)")
    
    # Data quality overview
    try:
        quality_scores = []
        for idx, profile in indonesian_profiles.iterrows():
            qc_data = json.loads(profile['qc_summary'])
            psal_quality = 1 - qc_data.get('psal_bad_frac', 0)
            quality_scores.append(psal_quality)
        
        avg_quality = sum(quality_scores) / len(quality_scores) * 100
        print(f"   • Average salinity data quality: {avg_quality:.1f}%")
    except:
        print(f"   • Quality assessment: Data available with QC flags")
    
    print(f"\n💡 For detailed analysis, I can:")
    print(f"   • Plot salinity vs depth profiles")  
    print(f"   • Show temporal changes in surface salinity")
    print(f"   • Compare with climatological averages")
    print(f"   • Identify water mass characteristics")

if __name__ == "__main__":
    demo_salinity_query()