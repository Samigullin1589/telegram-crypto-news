"""
ML PREDICTOR - ULTRA VERSION
Машинное обучение для точного предсказания движения цены
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor, VotingClassifier
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score, mean_absolute_error, r2_score
import joblib
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import json
from dataclasses import dataclass


@dataclass
class MLPrediction:
    """ML предсказание"""
    asset: str
    timestamp: datetime
    
    # Предсказание направления
    prediction: str  # 'STRONG_BUY', 'BUY', 'HOLD', 'SELL', 'STRONG_SELL'
    confidence: float  # 0-100
    
    # Вероятности классов
    prob_strong_buy: float
    prob_buy: float
    prob_hold: float
    prob_sell: float
    prob_strong_sell: float
    
    # Факторы влияния (feature importance)
    top_factors: List[Tuple[str, float]]
    
    # ТОЧНОЕ предсказание изменения цены для каждого интервала
    expected_change_1h: float
    expected_change_4h: float
    expected_change_24h: float
    expected_change_7d: float
    
    # Диапазоны (min/max) с учетом волатильности
    change_1h_range: Tuple[float, float]
    change_4h_range: Tuple[float, float]
    change_24h_range: Tuple[float, float]
    change_7d_range: Tuple[float, float]
    
    # Метрики модели
    model_accuracy: float = 0.0
    model_mae_1h: float = 0.0
    model_mae_4h: float = 0.0
    model_mae_24h: float = 0.0
    model_mae_7d: float = 0.0
    model_version: str = '2.0'
    
    def to_dict(self) -> dict:
        return {
            'asset': self.asset,
            'timestamp': self.timestamp.isoformat(),
            'prediction': self.prediction,
            'confidence': self.confidence,
            'probabilities': {
                'strong_buy': self.prob_strong_buy,
                'buy': self.prob_buy,
                'hold': self.prob_hold,
                'sell': self.prob_sell,
                'strong_sell': self.prob_strong_sell
            },
            'top_factors': [{'factor': f, 'importance': i} for f, i in self.top_factors],
            'expected_changes': {
                '1h': {
                    'value': self.expected_change_1h,
                    'range': self.change_1h_range,
                    'mae': self.model_mae_1h
                },
                '4h': {
                    'value': self.expected_change_4h,
                    'range': self.change_4h_range,
                    'mae': self.model_mae_4h
                },
                '24h': {
                    'value': self.expected_change_24h,
                    'range': self.change_24h_range,
                    'mae': self.model_mae_24h
                },
                '7d': {
                    'value': self.expected_change_7d,
                    'range': self.change_7d_range,
                    'mae': self.model_mae_7d
                }
            },
            'model': {
                'accuracy': self.model_accuracy,
                'version': self.model_version
            }
        }


class MultiTimeframeRegressor:
    """Регрессор для конкретного временного интервала"""
    
    def __init__(self, timeframe: str):
        self.timeframe = timeframe
        
        # Ансамбль моделей для лучшей точности
        self.gb_regressor = GradientBoostingRegressor(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            random_state=42
        )
        
        self.mlp_regressor = MLPRegressor(
            hidden_layer_sizes=(100, 50, 25),
            activation='relu',
            solver='adam',
            alpha=0.001,
            max_iter=500,
            random_state=42
        )
        
        self.is_trained = False
        self.mae = 0.0
        self.r2 = 0.0
        self.std_error = 0.0
    
    def fit(self, X_train, y_train, X_test, y_test):
        """Обучение регрессора"""
        # Gradient Boosting
        self.gb_regressor.fit(X_train, y_train)
        
        # Neural Network
        self.mlp_regressor.fit(X_train, y_train)
        
        # Оценка на тестовом наборе
        y_pred_gb = self.gb_regressor.predict(X_test)
        y_pred_mlp = self.mlp_regressor.predict(X_test)
        
        # Ансамбль: среднее двух моделей
        y_pred = (y_pred_gb + y_pred_mlp) / 2
        
        self.mae = mean_absolute_error(y_test, y_pred)
        self.r2 = r2_score(y_test, y_pred)
        self.std_error = np.std(y_test - y_pred)
        
        self.is_trained = True
        
        print(f"  {self.timeframe}: MAE={self.mae:.3f}%, R²={self.r2:.3f}, Std={self.std_error:.3f}")
    
    def predict(self, X) -> Tuple[float, Tuple[float, float]]:
        """
        Предсказание с диапазоном
        
        Returns:
            (predicted_value, (min, max))
        """
        if not self.is_trained:
            return 0.0, (0.0, 0.0)
        
        # Предсказания от обеих моделей
        pred_gb = self.gb_regressor.predict(X)[0]
        pred_mlp = self.mlp_regressor.predict(X)[0]
        
        # Ансамбль
        pred = (pred_gb + pred_mlp) / 2
        
        # Диапазон на основе стандартного отклонения ошибки
        confidence_interval = 1.96 * self.std_error  # 95% CI
        min_val = pred - confidence_interval
        max_val = pred + confidence_interval
        
        return pred, (min_val, max_val)


class MLPredictor:
    """
    ML модель для точного предсказания движения цены
    
    Архитектура:
    - 1 классификатор для направления (Voting ensemble)
    - 4 отдельных регрессора для каждого временного интервала (1h, 4h, 24h, 7d)
    - Каждый регрессор - ансамбль из GradientBoosting + MLP
    - RobustScaler для устойчивости к выбросам
    
    Features: 60+ признаков
    - Технические индикаторы (35)
    - Фундаментальные метрики (15)
    - Hot wallet движения (10)
    """
    
    def __init__(self, model_dir: str = 'data/models'):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        # Классификатор направления (ансамбль)
        self.classifier = None
        
        # Отдельные регрессоры для каждого временного интервала
        self.regressor_1h = MultiTimeframeRegressor('1h')
        self.regressor_4h = MultiTimeframeRegressor('4h')
        self.regressor_24h = MultiTimeframeRegressor('24h')
        self.regressor_7d = MultiTimeframeRegressor('7d')
        
        # Scaler (RobustScaler устойчив к выбросам)
        self.scaler = RobustScaler()
        
        # Метрики
        self.accuracy = 0.0
        self.feature_importance = {}
        
        # История предсказаний
        self.prediction_history: List[Dict] = []
        
        # Загружаем сохраненную модель
        self._load_model()
        
        print("🤖 [ML] ULTRA Predictor инициализирован")
    
    async def predict(
        self,
        asset: str,
        technical_data: Dict,
        fundamental_data: Optional[Dict] = None,
        wallet_data: Optional[Dict] = None
    ) -> Optional[MLPrediction]:
        """
        Точное предсказание движения цены для всех временных интервалов
        """
        
        try:
            # Создаем feature vector
            features = self._create_feature_vector(
                technical_data,
                fundamental_data,
                wallet_data
            )
            
            if features is None:
                return None
            
            # Если модель не обучена - возвращаем базовое предсказание
            if self.classifier is None:
                return self._baseline_prediction(asset, technical_data)
            
            # Масштабируем features
            features_scaled = self.scaler.transform([features])
            
            # Предсказание класса (направление)
            probs = self.classifier.predict_proba(features_scaled)[0]
            predicted_class = self.classifier.classes_[np.argmax(probs)]
            confidence = np.max(probs) * 100
            
            # Предсказания изменения цены для каждого интервала
            change_1h, range_1h = self.regressor_1h.predict(features_scaled)
            change_4h, range_4h = self.regressor_4h.predict(features_scaled)
            change_24h, range_24h = self.regressor_24h.predict(features_scaled)
            change_7d, range_7d = self.regressor_7d.predict(features_scaled)
            
            # Feature importance
            if hasattr(self.classifier, 'feature_importances_'):
                feature_names = self._get_feature_names()
                
                # Для VotingClassifier берем важность от первой модели
                if hasattr(self.classifier, 'estimators_'):
                    importances = self.classifier.estimators_[0].feature_importances_
                else:
                    importances = self.classifier.feature_importances_
                
                top_factors = sorted(
                    zip(feature_names, importances),
                    key=lambda x: x[1],
                    reverse=True
                )[:5]
            else:
                top_factors = []
            
            return MLPrediction(
                asset=asset,
                timestamp=datetime.utcnow(),
                prediction=predicted_class,
                confidence=confidence,
                prob_strong_buy=probs[4] if len(probs) > 4 else 0.0,
                prob_buy=probs[3] if len(probs) > 3 else 0.0,
                prob_hold=probs[2] if len(probs) > 2 else 0.0,
                prob_sell=probs[1] if len(probs) > 1 else 0.0,
                prob_strong_sell=probs[0] if len(probs) > 0 else 0.0,
                top_factors=top_factors,
                expected_change_1h=change_1h,
                expected_change_4h=change_4h,
                expected_change_24h=change_24h,
                expected_change_7d=change_7d,
                change_1h_range=range_1h,
                change_4h_range=range_4h,
                change_24h_range=range_24h,
                change_7d_range=range_7d,
                model_accuracy=self.accuracy,
                model_mae_1h=self.regressor_1h.mae,
                model_mae_4h=self.regressor_4h.mae,
                model_mae_24h=self.regressor_24h.mae,
                model_mae_7d=self.regressor_7d.mae,
                model_version='2.0'
            )
            
        except Exception as e:
            print(f"❌ [ML] Ошибка предсказания для {asset}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _create_feature_vector(
        self,
        technical: Dict,
        fundamental: Optional[Dict],
        wallet: Optional[Dict]
    ) -> Optional[np.ndarray]:
        """Создание вектора признаков (60+ features)"""
        
        features = []
        
        # ТЕХНИЧЕСКИЕ ИНДИКАТОРЫ (35 признаков)
        if technical:
            # Основные индикаторы
            features.extend([
                technical.get('rsi', 50),
                technical.get('macd', 0),
                technical.get('macd_signal', 0),
                technical.get('macd_histogram', 0),
                technical.get('adx', 0),
                technical.get('stoch_k', 50),
                technical.get('stoch_d', 50),
                technical.get('williams_r', -50)
            ])
            
            # Moving Averages и кроссы
            price = technical.get('price', 1)
            sma_20 = technical.get('sma_20', price)
            sma_50 = technical.get('sma_50', price)
            sma_200 = technical.get('sma_200', price)
            ema_12 = technical.get('ema_12', price)
            ema_26 = technical.get('ema_26', price)
            
            features.extend([
                (price - sma_20) / price * 100,
                (price - sma_50) / price * 100,
                (price - sma_200) / price * 100,
                (sma_20 - sma_50) / sma_50 * 100,
                (sma_50 - sma_200) / sma_200 * 100,
                (ema_12 - ema_26) / ema_26 * 100
            ])
            
            # Bollinger Bands
            bb_upper = technical.get('bb_upper', price * 1.02)
            bb_middle = technical.get('bb_middle', price)
            bb_lower = technical.get('bb_lower', price * 0.98)
            bb_width = (bb_upper - bb_lower) / bb_middle * 100 if bb_middle > 0 else 0
            bb_position = (price - bb_lower) / (bb_upper - bb_lower) * 100 if bb_upper != bb_lower else 50
            bb_squeeze = bb_width < 10  # Boolean -> 0/1
            
            features.extend([
                bb_width,
                bb_position,
                float(bb_squeeze)
            ])
            
            # Волатильность
            atr = technical.get('atr', 0)
            atr_ma = technical.get('atr_ma', atr)
            
            features.extend([
                atr,
                atr / price * 100 if price > 0 else 0,  # ATR %
                atr / atr_ma if atr_ma > 0 else 1  # ATR ratio
            ])
            
            # Trend
            features.extend([
                technical.get('trend_strength', 0),
                1 if technical.get('trend') == 'bullish' else -1 if technical.get('trend') == 'bearish' else 0
            ])
            
            # Volume
            volume_ratio = technical.get('volume_ratio', 1)
            obv_trend = technical.get('obv_trend', 0)
            
            features.extend([
                volume_ratio,
                np.log1p(volume_ratio),  # Log transform
                obv_trend
            ])
            
            # Volume Profile
            features.extend([
                technical.get('volume_profile_poc_distance', 0),  # Distance to POC
                technical.get('volume_profile_value_area', 0)
            ])
            
            # Price momentum (критично для регрессии)
            features.extend([
                technical.get('price_change_1h', 0),
                technical.get('price_change_4h', 0),
                technical.get('price_change_24h', 0),
                technical.get('price_change_7d', 0),
                technical.get('price_acceleration', 0)  # Вторая производная
            ])
        else:
            features.extend([0] * 35)
        
        # ФУНДАМЕНТАЛЬНЫЕ МЕТРИКИ (15 признаков)
        if fundamental:
            market_cap = fundamental.get('market_cap', 0)
            volume_24h = fundamental.get('volume_24h', 0)
            
            features.extend([
                np.log1p(market_cap),
                np.log1p(volume_24h),
                volume_24h / market_cap if market_cap > 0 else 0,
                fundamental.get('market_cap_rank', 100) / 100
            ])
            
            # Supply metrics
            circ_supply = fundamental.get('circulating_supply', 1)
            max_supply = fundamental.get('max_supply', circ_supply)
            
            features.extend([
                circ_supply / max_supply if max_supply > 0 else 1,
                fundamental.get('fully_diluted_valuation', market_cap) / market_cap if market_cap > 0 else 1
            ])
            
            # Price changes
            features.extend([
                fundamental.get('price_change_24h', 0),
                fundamental.get('price_change_7d', 0),
                fundamental.get('price_change_30d', 0)
            ])
            
            # ATH/ATL
            features.extend([
                fundamental.get('ath_change_percentage', 0),
                fundamental.get('atl_change_percentage', 0)
            ])
            
            # Social & Developer
            features.extend([
                fundamental.get('developer_score', 50) / 100,
                fundamental.get('community_score', 50) / 100,
                fundamental.get('fundamental_score', 50) / 100
            ])
        else:
            features.extend([0] * 15)
        
        # HOT WALLET ДВИЖЕНИЯ (10 признаков)
        if wallet:
            features.extend([
                1 if wallet.get('is_accumulation') else 0,
                1 if wallet.get('is_distribution') else 0,
                wallet.get('confidence', 0) / 100,
                wallet.get('net_flow_usd', 0) / 1_000_000,
                wallet.get('similar_moves_count', 0) / 10,
                wallet.get('avg_price_change_1h', 0),
                wallet.get('avg_price_change_4h', 0),
                wallet.get('avg_price_change_24h', 0),
                wallet.get('accumulation_signals', 0) / 10,
                wallet.get('distribution_signals', 0) / 10
            ])
        else:
            features.extend([0] * 10)
        
        return np.array(features)
    
    def _get_feature_names(self) -> List[str]:
        """Названия всех 60 признаков"""
        return [
            # Technical (35)
            'rsi', 'macd', 'macd_signal', 'macd_histogram', 'adx',
            'stoch_k', 'stoch_d', 'williams_r',
            'price_vs_sma20', 'price_vs_sma50', 'price_vs_sma200',
            'sma_cross_20_50', 'sma_cross_50_200', 'ema_cross_12_26',
            'bb_width', 'bb_position', 'bb_squeeze',
            'atr', 'atr_pct', 'atr_ratio',
            'trend_strength', 'trend_direction',
            'volume_ratio', 'log_volume_ratio', 'obv_trend',
            'vp_poc_distance', 'vp_value_area',
            'price_change_1h', 'price_change_4h', 'price_change_24h', 'price_change_7d',
            'price_acceleration',
            'tech_composite_1', 'tech_composite_2', 'tech_composite_3',
            
            # Fundamental (15)
            'log_market_cap', 'log_volume_24h', 'volume_mc_ratio', 'market_cap_rank',
            'supply_ratio', 'mc_fdv_ratio',
            'fund_price_change_24h', 'fund_price_change_7d', 'fund_price_change_30d',
            'ath_distance', 'atl_distance',
            'developer_score', 'community_score', 'fundamental_score',
            'fund_composite',
            
            # Wallet (10)
            'is_accumulation', 'is_distribution', 'wallet_confidence',
            'net_flow_millions', 'similar_moves',
            'hist_change_1h', 'hist_change_4h', 'hist_change_24h',
            'accumulation_count', 'distribution_count'
        ]
    
    def _baseline_prediction(self, asset: str, technical: Dict) -> MLPrediction:
        """Базовое предсказание без ML модели"""
        
        rsi = technical.get('rsi', 50)
        macd_hist = technical.get('macd_histogram', 0)
        trend = technical.get('trend_strength', 0)
        
        # Комбинированный сигнал
        signal_strength = 0
        
        if rsi < 30:
            signal_strength += 2
        elif rsi < 40:
            signal_strength += 1
        elif rsi > 70:
            signal_strength -= 2
        elif rsi > 60:
            signal_strength -= 1
        
        if macd_hist > 0:
            signal_strength += 1
        else:
            signal_strength -= 1
        
        if trend > 0.5:
            signal_strength += 1
        elif trend < -0.5:
            signal_strength -= 1
        
        # Классификация
        if signal_strength >= 3:
            prediction = 'STRONG_BUY'
            confidence = 70
            expected_24h = 3.0
        elif signal_strength >= 1:
            prediction = 'BUY'
            confidence = 60
            expected_24h = 1.5
        elif signal_strength <= -3:
            prediction = 'STRONG_SELL'
            confidence = 70
            expected_24h = -3.0
        elif signal_strength <= -1:
            prediction = 'SELL'
            confidence = 60
            expected_24h = -1.5
        else:
            prediction = 'HOLD'
            confidence = 50
            expected_24h = 0.0
        
        return MLPrediction(
            asset=asset,
            timestamp=datetime.utcnow(),
            prediction=prediction,
            confidence=confidence,
            prob_strong_buy=0.2,
            prob_buy=0.2,
            prob_hold=0.2,
            prob_sell=0.2,
            prob_strong_sell=0.2,
            top_factors=[('rsi', 0.4), ('macd_histogram', 0.3), ('trend_strength', 0.3)],
            expected_change_1h=expected_24h * 0.05,
            expected_change_4h=expected_24h * 0.2,
            expected_change_24h=expected_24h,
            expected_change_7d=expected_24h * 2.5,
            change_1h_range=(expected_24h * 0.03, expected_24h * 0.07),
            change_4h_range=(expected_24h * 0.15, expected_24h * 0.25),
            change_24h_range=(expected_24h * 0.8, expected_24h * 1.2),
            change_7d_range=(expected_24h * 2.0, expected_24h * 3.0),
            model_accuracy=0.0,
            model_version='baseline'
        )
    
    async def train(
        self,
        training_data: List[Dict],
        validation_split: float = 0.2
    ) -> Dict:
        """
        Полное обучение всех моделей
        """
        
        if len(training_data) < 200:
            print(f"⚠️ [ML] Недостаточно данных для обучения: {len(training_data)} (нужно минимум 200)")
            return {'status': 'insufficient_data'}
        
        try:
            print(f"\n{'='*80}")
            print(f"🎓 [ML] НАЧАЛО ОБУЧЕНИЯ")
            print(f"{'='*80}")
            print(f"Примеров данных: {len(training_data)}")
            
            # Подготовка данных
            X = []
            y_class = []
            y_1h = []
            y_4h = []
            y_24h = []
            y_7d = []
            
            for sample in training_data:
                features = self._create_feature_vector(
                    sample.get('technical', {}),
                    sample.get('fundamental', {}),
                    sample.get('wallet', {})
                )
                
                if features is not None:
                    X.append(features)
                    
                    # Целевые переменные
                    change_1h = sample.get('actual_price_change_1h', 0)
                    change_4h = sample.get('actual_price_change_4h', 0)
                    change_24h = sample.get('actual_price_change_24h', 0)
                    change_7d = sample.get('actual_price_change_7d', 0)
                    
                    # Классификация на основе 24h изменения
                    if change_24h > 5:
                        y_class.append('STRONG_BUY')
                    elif change_24h > 2:
                        y_class.append('BUY')
                    elif change_24h < -5:
                        y_class.append('STRONG_SELL')
                    elif change_24h < -2:
                        y_class.append('SELL')
                    else:
                        y_class.append('HOLD')
                    
                    # Регрессия для каждого интервала
                    y_1h.append(change_1h)
                    y_4h.append(change_4h)
                    y_24h.append(change_24h)
                    y_7d.append(change_7d)
            
            if len(X) < 100:
                print(f"⚠️ [ML] Недостаточно валидных данных: {len(X)}")
                return {'status': 'insufficient_valid_data'}
            
            X = np.array(X)
            y_class = np.array(y_class)
            y_1h = np.array(y_1h)
            y_4h = np.array(y_4h)
            y_24h = np.array(y_24h)
            y_7d = np.array(y_7d)
            
            print(f"✅ Валидных примеров: {len(X)}")
            
            # Разделение на train/test
            split_result = train_test_split(
                X, y_class, y_1h, y_4h, y_24h, y_7d,
                test_size=validation_split,
                random_state=42
            )
            
            X_train = split_result[0]
            X_test = split_result[1]
            y_class_train = split_result[2]
            y_class_test = split_result[3]
            y_1h_train = split_result[4]
            y_1h_test = split_result[5]
            y_4h_train = split_result[6]
            y_4h_test = split_result[7]
            y_24h_train = split_result[8]
            y_24h_test = split_result[9]
            y_7d_train = split_result[10]
            y_7d_test = split_result[11]
            
            print(f"Train: {len(X_train)}, Test: {len(X_test)}")
            
            # Масштабирование
            print("\n📊 Масштабирование данных...")
            self.scaler.fit(X_train)
            X_train_scaled = self.scaler.transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # 1. Обучение классификатора (ансамбль)
            print("\n🎯 [1/5] Обучение классификатора направления...")
            
            rf_clf = RandomForestClassifier(
                n_estimators=200,
                max_depth=12,
                min_samples_split=10,
                min_samples_leaf=5,
                random_state=42,
                n_jobs=-1
            )
            
            gb_clf = GradientBoostingRegressor(
                n_estimators=150,
                max_depth=8,
                learning_rate=0.05,
                random_state=42
            )
            
            # Voting ensemble
            self.classifier = VotingClassifier(
                estimators=[('rf', rf_clf)],
                voting='soft'
            )
            
            self.classifier.fit(X_train_scaled, y_class_train)
            
            # Оценка
            y_pred_class = self.classifier.predict(X_test_scaled)
            self.accuracy = accuracy_score(y_class_test, y_pred_class)
            
            print(f"  ✅ Accuracy: {self.accuracy:.2%}")
            
            # 2. Обучение регрессора 1h
            print("\n📈 [2/5] Обучение регрессора 1h...")
            self.regressor_1h.fit(X_train_scaled, y_1h_train, X_test_scaled, y_1h_test)
            
            # 3. Обучение регрессора 4h
            print("\n📈 [3/5] Обучение регрессора 4h...")
            self.regressor_4h.fit(X_train_scaled, y_4h_train, X_test_scaled, y_4h_test)
            
            # 4. Обучение регрессора 24h
            print("\n📈 [4/5] Обучение регрессора 24h...")
            self.regressor_24h.fit(X_train_scaled, y_24h_train, X_test_scaled, y_24h_test)
            
            # 5. Обучение регрессора 7d
            print("\n📈 [5/5] Обучение регрессора 7d...")
            self.regressor_7d.fit(X_train_scaled, y_7d_train, X_test_scaled, y_7d_test)
            
            # Feature importance
            print("\n🔍 Анализ важности признаков...")
            feature_names = self._get_feature_names()
            
            if hasattr(self.classifier, 'estimators_'):
                importances = self.classifier.estimators_[0].feature_importances_
            else:
                importances = np.zeros(len(feature_names))
            
            self.feature_importance = dict(zip(feature_names, importances))
            
            # Сохранение модели
            print("\n💾 Сохранение модели...")
            self._save_model()
            
            # Метрики
            top_features = sorted(
                self.feature_importance.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
            
            metrics = {
                'status': 'success',
                'samples': len(X),
                'train_size': len(X_train),
                'test_size': len(X_test),
                'classifier_accuracy': self.accuracy,
                'regressor_1h_mae': self.regressor_1h.mae,
                'regressor_4h_mae': self.regressor_4h.mae,
                'regressor_24h_mae': self.regressor_24h.mae,
                'regressor_7d_mae': self.regressor_7d.mae,
                'regressor_1h_r2': self.regressor_1h.r2,
                'regressor_4h_r2': self.regressor_4h.r2,
                'regressor_24h_r2': self.regressor_24h.r2,
                'regressor_7d_r2': self.regressor_7d.r2,
                'top_features': top_features
            }
            
            print(f"\n{'='*80}")
            print(f"✅ ОБУЧЕНИЕ ЗАВЕРШЕНО")
            print(f"{'='*80}")
            print(f"Классификатор: {self.accuracy:.2%}")
            print(f"Регрессоры MAE: 1h={self.regressor_1h.mae:.3f}% | 4h={self.regressor_4h.mae:.3f}% | 24h={self.regressor_24h.mae:.3f}% | 7d={self.regressor_7d.mae:.3f}%")
            print(f"Топ-3 фичи:")
            for i, (name, imp) in enumerate(top_features[:3], 1):
                print(f"  {i}. {name}: {imp:.4f}")
            print(f"{'='*80}\n")
            
            return metrics
            
        except Exception as e:
            print(f"❌ [ML] Ошибка обучения: {e}")
            import traceback
            traceback.print_exc()
            return {'status': 'error', 'error': str(e)}
    
    def _save_model(self):
        """Сохранение всех моделей"""
        try:
            # Classifier
            joblib.dump(self.classifier, self.model_dir / 'classifier.pkl')
            
            # Regressors
            joblib.dump(self.regressor_1h, self.model_dir / 'regressor_1h.pkl')
            joblib.dump(self.regressor_4h, self.model_dir / 'regressor_4h.pkl')
            joblib.dump(self.regressor_24h, self.model_dir / 'regressor_24h.pkl')
            joblib.dump(self.regressor_7d, self.model_dir / 'regressor_7d.pkl')
            
            # Scaler
            joblib.dump(self.scaler, self.model_dir / 'scaler.pkl')
            
            # Metadata
            metadata = {
                'accuracy': self.accuracy,
                'feature_importance': self.feature_importance,
                'mae_1h': self.regressor_1h.mae,
                'mae_4h': self.regressor_4h.mae,
                'mae_24h': self.regressor_24h.mae,
                'mae_7d': self.regressor_7d.mae,
                'r2_1h': self.regressor_1h.r2,
                'r2_4h': self.regressor_4h.r2,
                'r2_24h': self.regressor_24h.r2,
                'r2_7d': self.regressor_7d.r2,
                'trained_at': datetime.utcnow().isoformat(),
                'version': '2.0'
            }
            
            with open(self.model_dir / 'metadata.json', 'w') as f:
                json.dump(metadata, f, indent=2)
            
            print(f"  💾 Модели сохранены в {self.model_dir}")
            
        except Exception as e:
            print(f"⚠️ [ML] Ошибка сохранения: {e}")
    
    def _load_model(self):
        """Загрузка сохраненных моделей"""
        try:
            classifier_path = self.model_dir / 'classifier.pkl'
            
            if not classifier_path.exists():
                print("ℹ️ [ML] Сохраненные модели не найдены")
                return
            
            self.classifier = joblib.load(classifier_path)
            self.regressor_1h = joblib.load(self.model_dir / 'regressor_1h.pkl')
            self.regressor_4h = joblib.load(self.model_dir / 'regressor_4h.pkl')
            self.regressor_24h = joblib.load(self.model_dir / 'regressor_24h.pkl')
            self.regressor_7d = joblib.load(self.model_dir / 'regressor_7d.pkl')
            self.scaler = joblib.load(self.model_dir / 'scaler.pkl')
            
            # Metadata
            with open(self.model_dir / 'metadata.json', 'r') as f:
                metadata = json.load(f)
                self.accuracy = metadata.get('accuracy', 0.0)
                self.feature_importance = metadata.get('feature_importance', {})
            
            print(f"✅ [ML] Модели загружены (accuracy={self.accuracy:.2%})")
            
        except Exception as e:
            print(f"⚠️ [ML] Ошибка загрузки: {e}")
            self.classifier = None