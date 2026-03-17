import asyncio
import logging
from strategy.dynamic_weights import DynamicWeightOptimizer

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def main():
    logger = logging.getLogger("WeightUpdater")
    logger.info("Initializing dynamic weight optimizer...")
    
    optimizer = DynamicWeightOptimizer()
    
    logger.info("Running weight update...")
    optimizer.update_weights()
    
    logger.info("Weight update complete.")

if __name__ == "__main__":
    asyncio.run(main())
