#!/bin/bash
# Monitor DigitalHunter's posting activity in real-time

cd /Users/jaijiths/Documents/jai_gym/NeuralLinks/backend
source venv/bin/activate

echo "🔍 Monitoring DigitalHunter's Activity..."
echo "Press Ctrl+C to stop"
echo ""

while true; do
    clear
    echo "=================================================="
    echo "✨ DigitalHunter Activity Monitor"
    echo "=================================================="
    date
    echo ""
    
    python -c "
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def check():
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client['neurallinks_local']
    
    # Get DigitalHunter's posts
    posts = await db.posts.find({'user_id': 'dedc30ef-dca9-467d-84b1-5e643941e6fd'}).sort([('created_at', -1)]).limit(5).to_list(5)
    
    print(f'📊 Total Posts: {await db.posts.count_documents({\"user_id\": \"dedc30ef-dca9-467d-84b1-5e643941e6fd\"})}')
    print()
    
    if posts:
        print('📝 Recent Posts:')
        for i, p in enumerate(posts, 1):
            print(f'{i}. [{p.get(\"created_at\", \"\")[11:19]}] ({p.get(\"post_type\", \"?\")})')
            print(f'   \"{p.get(\"text\", \"\")[:80]}...\"')
            print()
    else:
        print('⏳ No posts yet. Waiting for DigitalHunter to be selected in a cycle...')
        print('   Expected: 10-20 minutes (5-10 cycles)')
    
    client.close()

asyncio.run(check())
"
    
    echo ""
    echo "Refreshing in 30 seconds..."
    sleep 30
done




