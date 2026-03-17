import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List
from collections import defaultdict

from storage.database import Database
from config import BASE_DIR
from utils.logger import get_logger

log = get_logger("strategy.dynamic_weights")

WEIGHTS_FILE_PATH = os.path.join(BASE_DIR, "config", "dynamic_weights.json")

class DynamicWeightOptimizer:
    """
    Optimizes confidence weights for advanced analytics features based on historical performance.
    """

    def __init__(self, db: Database = None, lookback_days: int = 30):
        self.db = db or Database()
        self.lookback_days = lookback_days
        self.weights: Dict[str, float] = {}
        
        # Default weights acting as a fallback if no statistical data is available yet
        self.default_weights = {
            "bias_STRONG_BULLISH": 8.0,
            "bias_STRONG_BEARISH": 8.0,
            "bias_LEAN_BULLISH": 4.0,
            "bias_LEAN_BEARISH": 4.0,
            "cvd_divergence": -5.0,
            "stacked_imbalances": 6.0,
            "near_value_area": 3.0,
            "near_order_block": 4.0,
            "near_fvg": 3.0,
            "liquidity_grabs": 6.0,
            "bos": 5.0,
            "structure_shift": 5.0,
            "liq_sweep_reversal": 7.0,
            "liq_cascade_danger": -10.0,
            "extreme_funding": 3.0,
            "oi_momentum": 4.0,
            "oi_reversal": 3.0,
            "extreme_ls_ratio_favor": 4.0,
            "phase1_boost_max": 8.0,
            "phase2_whale_agree": 12.0,
            "phase2_whale_conflict": -8.0,
            "phase3_strategies_agree": 10.0,
            "phase3_strategies_conflict": -5.0,
            "vwap_extreme_3sigma": 10.0,
            "vwap_strong_2sigma": 8.0,
            "reversal_pattern_agree": 6.0,
            "momentum_over_80": 5.0,
            "momentum_divergence": -5.0,
            "ict_killzone_active": 4.0,
            "ict_silver_bullet": 8.0,
            "ict_ote": 6.0,
            "ict_premium_discount_extreme": 5.0,
            "ict_power_of_3_phase": 6.0,
            "ict_liquidity_pool": 5.0
        }
        
        self.load_weights()

    def _extract_features(self, advanced_data: Dict, steps: List[str], direction: str) -> List[str]:
        """Flattens the nested dictionary into a list of active feature strings."""
        features = []
        if not advanced_data:
            return features

        of = advanced_data.get("advanced_orderflow", {})
        bias = of.get("overall_bias")
        if bias in ["STRONG_BULLISH", "STRONG_BEARISH", "LEAN_BULLISH", "LEAN_BEARISH"]:
            features.append(f"bias_{bias}")

        cvd_div = of.get("cvd_divergence", {})
        if cvd_div.get("divergence") in ("BULLISH", "BEARISH"):
            features.append("cvd_divergence")

        fp = advanced_data.get("footprint_imbalance", {})
        if fp.get("stacked_imbalances_detected"):
            features.append("stacked_imbalances")

        vp = advanced_data.get("volume_profile", {})
        if vp.get("poc") and vp.get("val") and vp.get("vah"):
            features.append("near_value_area")

        pd = advanced_data.get("price_delivery", {})
        if pd.get("nearest_ob"):
            features.append("near_order_block")
        if pd.get("nearest_fvg"):
            features.append("near_fvg")
        if pd.get("total_liquidity_grabs", 0) > 0:
            features.append("liquidity_grabs")
        if pd.get("total_bos", 0) > 0:
            features.append("bos")
            
        structure = pd.get("structure_shift", {})
        if structure.get("shift_detected"):
             features.append("structure_shift")

        crypto = advanced_data.get("crypto", {})
        sweeps = crypto.get("liquidation_sweeps", [])
        if sweeps and any(s.get("reversed") for s in sweeps):
            features.append("liq_sweep_reversal")

        cascade = crypto.get("liquidation_cascade", {})
        if cascade.get("cascade_detected"):
            features.append("liq_cascade_danger")

        funding = crypto.get("funding", {})
        if funding.get("is_extreme"):
            features.append("extreme_funding")

        oi = crypto.get("open_interest", {})
        if oi:
            interp = oi.get("interpretation", "")
            if interp in ("BULLISH_MOMENTUM", "BEARISH_MOMENTUM"):
                features.append("oi_momentum")
            elif interp == "POTENTIAL_REVERSAL":
                features.append("oi_reversal")

        ls_ratio = crypto.get("long_short_ratio", {})
        if ls_ratio:
            ratio_val = ls_ratio.get("ratio", 1.0)
            if (ratio_val > 2.0 and direction == "SHORT") or (ratio_val < 0.5 and direction == "LONG"):
                features.append("extreme_ls_ratio_favor")

        # Phase 1
        phase1 = advanced_data.get("phase1")
        if phase1 and phase1.get("signal") != "NEUTRAL":
            features.append("phase1_boost_max")

        # Phase 2 Whale
        phase2 = advanced_data.get("phase2_whale")
        if phase2 and phase2.get("whale_signal") != "NEUTRAL":
            if phase2["whale_signal"] == direction:
                features.append("phase2_whale_agree")
            else:
                features.append("phase2_whale_conflict")

        # Phase 3 Strategies
        phase3 = advanced_data.get("phase3_strategies")
        if phase3 and phase3.get("signal") != "NEUTRAL":
            if phase3["signal"] == direction:
                features.append("phase3_strategies_agree")
            else:
                features.append("phase3_strategies_conflict")

        # VWAP Bands
        vwap = advanced_data.get("vwap_bands")
        if vwap:
            vwap_signal = vwap.get("signal")
            dev = abs(vwap.get("deviation_from_vwap", 0))
            if (direction == "LONG" and vwap_signal == "OVERSOLD") or (direction == "SHORT" and vwap_signal == "OVERBOUGHT"):
                if dev >= 3.0:
                    features.append("vwap_extreme_3sigma")
                elif dev >= 2.0:
                    features.append("vwap_strong_2sigma")

        # Reversal Patterns
        reversal = advanced_data.get("reversal_patterns")
        if reversal and reversal.get("best_pattern"):
            pattern = reversal["best_pattern"]
            if pattern["direction"] == direction:
                features.append("reversal_pattern_agree")

        # Momentum
        momentum = advanced_data.get("momentum")
        if momentum:
            score = momentum.get("momentum_score", 0)
            if score >= 80:
                features.append("momentum_over_80")
            if momentum.get("divergence_detected"):
                features.append("momentum_divergence")

        # ICT
        killzone = advanced_data.get("ict_killzone")
        if killzone and killzone.get("active"):
            features.append("ict_killzone_active")
            
        silver = advanced_data.get("ict_silver_bullet")
        if silver and silver.get("is_silver_bullet"):
            features.append("ict_silver_bullet")
            
        ote = advanced_data.get("ict_ote")
        if ote and ote.get("ote_entry", {}).get("at_ote"):
            features.append("ict_ote")

        pd_zone = advanced_data.get("ict_premium_discount")
        if pd_zone and pd_zone.get("zone") != "EQUILIBRIUM":
            features.append("ict_premium_discount_extreme")

        power3 = advanced_data.get("ict_power_of_3")
        if power3 and power3.get("phase") != "UNKNOWN":
            features.append("ict_power_of_3_phase")

        liq_pools = advanced_data.get("ict_liquidity_pools")
        if liq_pools and liq_pools.get("at_level"):
            features.append("ict_liquidity_pool")

        return features

    def calculate_adjustment(self, advanced_data: Dict, steps: List[str], direction: str) -> float:
        """Calculates total adjustment by fetching dynamic weights for active features.
        
        Returns 0 if insufficient sample size for reliable dynamic weights.
        """
        # Check if we have sufficient sample size for dynamic weights
        if not self._has_sufficient_sample():
            log.debug("Insufficient sample size for dynamic weights, using defaults only")
            features = self._extract_features(advanced_data, steps, direction)
            adj = 0.0
            for feature in features:
                weight = self.default_weights.get(feature, 0.0)
                adj += weight
                log.debug(f"Applied default weight: {feature} = {weight:+.2f}")
            return adj
        
        # Use dynamic weights
        features = self._extract_features(advanced_data, steps, direction)
        adj = 0.0
        
        for feature in features:
            weight = self.weights.get(feature, self.default_weights.get(feature, 0.0))
            adj += weight
            log.debug(f"Applied dynamic weight: {feature} = {weight:+.2f}")
            
        return adj
    
    def _has_sufficient_sample(self, min_trades: int = 30) -> bool:
        """Check if we have sufficient historical data for dynamic weights.
        
        Args:
            min_trades: Minimum number of trades required (default: 30)
            
        Returns:
            True if sufficient sample size, False otherwise
        """
        if not self.weights:
            return False
            
        conn = self.db._get_conn()
        try:
            query = """
                SELECT COUNT(*) as count
                FROM signals s
                JOIN signal_outcomes o ON s.signal_id = o.signal_id
                WHERE o.outcome IN ('WIN', 'LOSS') 
                  AND s.created_at >= datetime('now', ?)
            """
            row = conn.execute(query, (f"-{self.lookback_days} days",)).fetchone()
            count = row['count'] if row else 0
            
            if count < min_trades:
                log.debug(f"Sample size {count} < minimum {min_trades} for dynamic weights")
                return False
            
            return True
        except Exception as e:
            log.error(f"Error checking sample size: {e}")
            return False
        finally:
            conn.close()
    
    def get_sample_size(self) -> int:
        """Get current sample size for dynamic weights.
        
        Returns:
            Number of trades in lookback period
        """
        conn = self.db._get_conn()
        try:
            query = """
                SELECT COUNT(*) as count
                FROM signals s
                JOIN signal_outcomes o ON s.signal_id = o.signal_id
                WHERE o.outcome IN ('WIN', 'LOSS') 
                  AND s.created_at >= datetime('now', ?)
            """
            row = conn.execute(query, (f"-{self.lookback_days} days",)).fetchone()
            return row['count'] if row else 0
        except Exception as e:
            log.error(f"Error getting sample size: {e}")
            return 0
        finally:
            conn.close()

    def get_feature_info(self, advanced_data: Dict, steps: List[str], direction: str) -> List[Dict[str, Any]]:
         """Returns detailed info on active features and their weights for logging."""
         features = self._extract_features(advanced_data, steps, direction)
         info = []
         for f in features:
            weight = self.weights.get(f, self.default_weights.get(f, 0.0))
            is_dynamic = f in self.weights
            info.append({"feature": f, "weight": weight, "dynamic": is_dynamic})
         return info

    def update_weights(self):
        """
        Analyzes historical data and recalculates weights dynamically.
        Penalty/Bonus based on win rate of the feature vs baseline win rate.
        """
        log.info(f"Starting dynamic weight optimization (Lookback: {self.lookback_days} days)")
        
        conn = self.db._get_conn()
        try:
            # Fetch historical trades with outcomes
            query = """
                SELECT s.signal_id, s.signal_type, s.advanced_analytics, s.steps_confirmed, 
                       o.outcome, o.pnl_pct
                FROM signals s
                JOIN signal_outcomes o ON s.signal_id = o.signal_id
                WHERE o.outcome IN ('WIN', 'LOSS') 
                  AND s.created_at >= datetime('now', ?)
            """
            rows = conn.execute(query, (f"-{self.lookback_days} days",)).fetchall()
            
            if not rows or len(rows) < 20: # Require minimum sample size
                log.info(f"Insufficient historical data ({len(rows)} trades) to optimize weights. Using defaults/cached.")
                return False

            total_trades = len(rows)
            total_wins = sum(1 for r in rows if r['outcome'] == 'WIN')
            baseline_win_rate = total_wins / total_trades
            
            log.info(f"Baseline Win Rate across {total_trades} trades: {baseline_win_rate:.1%}")

            # Collect stats per feature
            feature_stats = defaultdict(lambda: {"total": 0, "wins": 0, "pnl_sum": 0.0})

            for row in rows:
                adv_data_raw = row['advanced_analytics']
                if not adv_data_raw:
                     continue
                     
                try:
                    adv_data = json.loads(adv_data_raw)
                except json.JSONDecodeError:
                    continue
                
                # We need to approximate direction and steps
                direction = row['signal_type']
                steps_count = row['steps_confirmed']
                # Fake steps list just to pass the length requirement in _extract_features if needed, 
                # though _extract_features only checks for existence or uses content
                mock_steps = ["STEP1", "STEP2", "STEP3", "STEP4"][:steps_count]
                
                features = self._extract_features(adv_data, mock_steps, direction)
                
                for f in features:
                    feature_stats[f]["total"] += 1
                    if row['outcome'] == 'WIN':
                         feature_stats[f]["wins"] += 1
                    if row['pnl_pct'] is not None:
                         feature_stats[f]["pnl_sum"] += row['pnl_pct']

            # Calculate new weights
            new_weights = {}
            for feature, stats in feature_stats.items():
                if stats["total"] < 5: # Minimum occurrences to matter
                    continue
                
                f_win_rate = stats["wins"] / stats["total"]
                win_rate_diff = f_win_rate - baseline_win_rate
                
                # Weight logic: 
                # - Center around 0. 
                # - If standard default is positive (bonus), we adjust it based on WR diff.
                # - If feature has +10% WR over baseline, give it +5 to +10
                # - If feature has -10% WR under baseline, give it penalty
                
                base_weight = self.default_weights.get(feature, 0.0)
                
                # Sigmoidal mapping or linear scaling
                # e.g., 5% improvement in WR -> +2 points
                adjustment = win_rate_diff * 100 * 0.4 # 10% diff = 4 points
                
                # Combine base intent with real performance factor
                if base_weight >= 0:
                     # Positive features
                     dynamic_w = base_weight + adjustment
                     dynamic_w = max(-5.0, min(12.0, dynamic_w)) # Cap between -5 and +12
                else:
                     # Negative features (warnings) - if they actually warned against a loss (win rate drops if ignored)
                     # If WR drops when this feature is present, the warning is VALID -> keep it negative
                     # If WR is same/higher, the warning is NOISE -> pull it to 0
                     if win_rate_diff < 0: # It correctly predicts losses
                         dynamic_w = base_weight + (win_rate_diff * 100 * 0.2)
                         dynamic_w = max(-15.0, min(-2.0, dynamic_w))
                     else:
                         dynamic_w = 0.0 # Noise
                         
                new_weights[feature] = round(dynamic_w, 2)
                log.info(f"Feature: {feature:30s} | N={stats['total']:3d} | WR={f_win_rate:.1%} | Diff={win_rate_diff*100:+.1f}% | New Weight: {new_weights[feature]:+.2f} (Base: {base_weight:+.2f})")

            if new_weights:
                self.weights = new_weights
                self.save_weights()
                log.info(f"Successfully optimized {len(self.weights)} dynamic weights.")
                return True
            else:
                log.warning("No significant features reached occurrence threshold.")
                return False

        except Exception as e:
            log.error(f"Error updating dynamic weights: {e}", exc_info=True)
            return False
        finally:
            conn.close()

    def save_weights(self):
        """Persists current weights to JSON cache."""
        try:
            os.makedirs(os.path.dirname(WEIGHTS_FILE_PATH), exist_ok=True)
            with open(WEIGHTS_FILE_PATH, 'w') as f:
                json.dump({
                    "last_updated": datetime.utcnow().isoformat(),
                    "lookback_days": self.lookback_days,
                    "weights": self.weights
                }, f, indent=4)
        except Exception as e:
            log.error(f"Failed to save dynamic weights cache: {e}")

    def load_weights(self):
        """Loads weights from JSON cache if present."""
        if not os.path.exists(WEIGHTS_FILE_PATH):
            return
        
        try:
            with open(WEIGHTS_FILE_PATH, 'r') as f:
                data = json.load(f)
                
            self.weights = data.get("weights", {})
            last_dt = datetime.fromisoformat(data.get("last_updated", "2000-01-01T00:00:00"))
            
            # If weights are super old, log it
            if datetime.utcnow() - last_dt > timedelta(days=7):
                 log.warning(f"Dynamic weights cache is older than 7 days ({data.get('last_updated')}). Optimization required.")
            else:
                 log.info(f"Loaded {len(self.weights)} dynamic weights from {data.get('last_updated')}")
        except Exception as e:
            log.error(f"Failed to load dynamic weights cache: {e}")
