import asyncio
import sys
import os
from datetime import datetime, timedelta

# Ensure imports work
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.storyline_generator import storyline_generator
from services.storyline_manager import StorylineManager

async def regenerate_history(days: int = 7):
    manager = StorylineManager()
    
    # 1. Ensure seed series exist
    await manager.ensure_seed_series()
    
    # 2. Iterate backwards from today
    today = datetime.now()
    
    for i in range(days):
        target_date = today - timedelta(days=i)
        date_str = target_date.strftime("%Y-%m-%d")
        
        print(f"\nProcessing {date_str}...")
        try:
            # Generate new storylines (this will overwrite old ones for that date)
            storylines = await storyline_generator.generate_daily_storylines(date_str)
            print(f"  -> Generated {len(storylines)} storylines.")
            
            for sl in storylines:
                print(f"     - {sl.title} ({sl.series_title})")
                
        except Exception as e:
            print(f"  -> Error processing {date_str}: {e}")
            import traceback
            traceback.print_exc()

    print("\nBatch regeneration completed.")
    
    # Display final Series status
    series_list = await manager.get_all_series()
    print(f"\nActive Series Summary:")
    for s in series_list:
        print(f"- {s['title']} (Updated: {s['updated_at']})")

if __name__ == "__main__":
    try:
        days = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    except ValueError:
        days = 7
        
    asyncio.run(regenerate_history(days))
