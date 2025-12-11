#!/usr/bin/env python3
"""
Simple server to receive missed call notifications from IFTTT
and integrate with existing task generation system.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json
import logging
from datetime import datetime
from typing import Optional

app = FastAPI(title="PI2PRINTER Missed Call Server", version="1.0.0")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MissedCallData(BaseModel):
    caller: Optional[str] = "Unknown"
    number: Optional[str] = "Unknown"
    time: Optional[str] = None
    source: Optional[str] = None

@app.post("/missed_call")
async def handle_missed_call(data: MissedCallData):
    """Handle incoming missed call notification from IFTTT"""
    try:
        # Extract call details
        caller = data.caller
        number = data.number
        call_time = data.time or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        logger.info(f"Missed call from {caller} ({number}) at {call_time}")
        
        # Create task from missed call
        task_data = {
            'type': 'missed_call',
            'caller': caller,
            'number': number,
            'time': call_time,
            'description': f"Missed call from {caller} ({number})"
        }
        
        # TODO: Integrate with existing task generation system
        # Example: create_task_from_data(task_data)
        
        # For now, just log the task data
        print(f"TASK GENERATED: {json.dumps(task_data, indent=2)}")
        
        return {
            "status": "success",
            "message": f"Processed missed call from {caller}"
        }
        
    except Exception as e:
        logger.error(f"Error processing missed call: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == '__main__':
    import uvicorn
    print("Starting missed call notification server...")
    print("Listening for IFTTT webhooks on port 5000")
    uvicorn.run(app, host="0.0.0.0", port=5000)
