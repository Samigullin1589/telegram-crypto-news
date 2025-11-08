"""
Компонент анализа и оптимизации запросов

Архитектурные решения:
- EXPLAIN ANALYZE для медленных запросов
- Обнаружение N+1 queries
- Рекомендации по индексам на основе запросов
- Анализ планов выполнения
- Обнаружение картезианских произведений
"""

import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Tuple


class QueryType(Enum):
    """Типы запросов"""
    SELECT = 'select'
    INSERT = 'insert'
    UPDATE = 'update'
    DELETE = 'delete'
    OTHER = 'other'


class QueryIssue(Enum):
    """Проблемы запросов"""
    MISSING_INDEX = 'missing_index'
    FULL_TABLE_SCAN = 'full_table_scan'
    CARTESIAN_PRODUCT = 'cartesian_product'
    N_PLUS_ONE = 'n_plus_one'
    INEFFICIENT_JOIN = 'inefficient_join'
    MISSING_WHERE = 'missing_where'
    SELECT_STAR = 'select_star'
    SUBOPTIMAL_SORT = 'suboptimal_sort'


@dataclass
class QueryPlan:
    """План выполнения запроса"""
    query_hash: str
    query_text: str
    plan_json: Dict[str, Any]
    execution_time_ms: float
    planning_time_ms: float
    total_cost: float
    analyzed_at: float
    
    # Извлеченные характеристики
    uses_index: bool = False
    has_sequential_scan: bool = False
    has_nested_loop: bool = False
    rows_estimated: int = 0
    rows_actual: int = 0
    
    @property
    def estimation_accuracy(self) -> float:
        """Точность оценки строк планировщиком"""
        if self.rows_estimated == 0:
            return 0.0
        return min(self.rows_actual, self.rows_estimated) / max(self.rows_actual, self.rows_estimated)


@dataclass
class QueryRecommendation:
    """Рекомендация по оптимизации запроса"""
    query_hash: str
    issue: QueryIssue
    severity: str  # 'high', 'medium', 'low'
    description: str
    recommendation: str
    estimated_improvement: str
    tables_affected: List[str] = field(default_factory=list)
    columns_affected: List[str] = field(default_factory=list)


class QueryAnalyzer:
    """
    Анализ и оптимизация запросов
    
    Ответственности:
    - Анализ планов выполнения
    - Обнаружение проблемных паттернов
    - Генерация рекомендаций
    - Отслеживание N+1 queries
    """
    
    def __init__(
        self,
        enabled: bool = True,
        
        # Анализ планов
        analyze_slow_queries: bool = True,
        slow_query_threshold_ms: float = 1000.0,
        auto_explain_threshold_ms: float = 5000.0,
        
        # Обнаружение паттернов
        detect_n_plus_one: bool = True,
        n_plus_one_threshold: int = 10,  # Количество похожих запросов
        detect_missing_indexes: bool = True,
        detect_cartesian_products: bool = True,
        
        # Рекомендации
        generate_recommendations: bool = True,
        min_recommendation_impact: str = 'medium'
    ):
        self.enabled = enabled
        self.analyze_slow_queries = analyze_slow_queries
        self.slow_query_threshold_ms = slow_query_threshold_ms
        self.auto_explain_threshold_ms = auto_explain_threshold_ms
        
        self.detect_n_plus_one = detect_n_plus_one
        self.n_plus_one_threshold = n_plus_one_threshold
        self.detect_missing_indexes = detect_missing_indexes
        self.detect_cartesian_products = detect_cartesian_products
        
        self.generate_recommendations = generate_recommendations
        self.min_recommendation_impact = min_recommendation_impact
        
        # Хранилище планов
        self._query_plans: Dict[str, QueryPlan] = {}
        self._recommendations: Dict[str, List[QueryRecommendation]] = {}
        
        # Паттерны запросов для обнаружения N+1
        self._query_patterns: Dict[str, List[Tuple[float, str]]] = {}  # pattern -> [(timestamp, query)]
        
        # Метрики
        self._total_plans_analyzed = 0
        self._total_recommendations_generated = 0
        self._n_plus_one_detected = 0
        self._missing_indexes_detected = 0
        self._cartesian_products_detected = 0
    
    def analyze_query_plan(
        self,
        query_hash: str,
        query_text: str,
        plan_json: Dict[str, Any],
        execution_time_ms: float,
        planning_time_ms: float
    ) -> QueryPlan:
        """
        Анализ плана выполнения запроса
        
        Args:
            query_hash: Хэш запроса
            query_text: Текст запроса
            plan_json: JSON план из EXPLAIN
            execution_time_ms: Время выполнения
            planning_time_ms: Время планирования
            
        Returns:
            Проанализированный план
        """
        plan = QueryPlan(
            query_hash=query_hash,
            query_text=query_text,
            plan_json=plan_json,
            execution_time_ms=execution_time_ms,
            planning_time_ms=planning_time_ms,
            total_cost=plan_json.get('Total Cost', 0.0),
            analyzed_at=time.time()
        )
        
        # Извлечение характеристик из плана
        plan.uses_index = self._plan_uses_index(plan_json)
        plan.has_sequential_scan = self._plan_has_sequential_scan(plan_json)
        plan.has_nested_loop = self._plan_has_nested_loop(plan_json)
        plan.rows_estimated = plan_json.get('Plan Rows', 0)
        plan.rows_actual = plan_json.get('Actual Rows', 0)
        
        self._query_plans[query_hash] = plan
        self._total_plans_analyzed += 1
        
        # Генерация рекомендаций
        if self.generate_recommendations:
            self._generate_query_recommendations(plan)
        
        return plan
    
    def _plan_uses_index(self, plan: Dict[str, Any]) -> bool:
        """Проверка использования индексов в плане"""
        node_type = plan.get('Node Type', '')
        
        if 'Index' in node_type:
            return True
        
        # Рекурсивная проверка дочерних узлов
        for child in plan.get('Plans', []):
            if self._plan_uses_index(child):
                return True
        
        return False
    
    def _plan_has_sequential_scan(self, plan: Dict[str, Any]) -> bool:
        """Проверка наличия Seq Scan в плане"""
        node_type = plan.get('Node Type', '')
        
        if node_type == 'Seq Scan':
            return True
        
        for child in plan.get('Plans', []):
            if self._plan_has_sequential_scan(child):
                return True
        
        return False
    
    def _plan_has_nested_loop(self, plan: Dict[str, Any]) -> bool:
        """Проверка наличия Nested Loop в плане"""
        node_type = plan.get('Node Type', '')
        
        if node_type == 'Nested Loop':
            return True
        
        for child in plan.get('Plans', []):
            if self._plan_has_nested_loop(child):
                return True
        
        return False
    
    def _generate_query_recommendations(self, plan: QueryPlan) -> None:
        """Генерация рекомендаций на основе плана"""
        recommendations = []
        
        # Проблема: Sequential Scan на большой таблице
        if plan.has_sequential_scan and plan.rows_actual > 1000:
            if self.detect_missing_indexes:
                tables = self._extract_tables_from_query(plan.query_text)
                columns = self._extract_where_columns(plan.query_text)
                
                recommendations.append(QueryRecommendation(
                    query_hash=plan.query_hash,
                    issue=QueryIssue.MISSING_INDEX,
                    severity='high',
                    description=f'Sequential scan on {plan.rows_actual} rows',
                    recommendation=f'Consider creating index on columns: {", ".join(columns)}',
                    estimated_improvement='50-90% faster execution',
                    tables_affected=tables,
                    columns_affected=columns
                ))
                self._missing_indexes_detected += 1
        
        # Проблема: Плохая оценка планировщика
        if plan.estimation_accuracy < 0.1 and plan.rows_actual > 100:
            recommendations.append(QueryRecommendation(
                query_hash=plan.query_hash,
                issue=QueryIssue.INEFFICIENT_JOIN,
                severity='medium',
                description=f'Planner estimated {plan.rows_estimated} rows but got {plan.rows_actual}',
                recommendation='Run ANALYZE on affected tables or adjust statistics target',
                estimated_improvement='Better query plans',
                tables_affected=self._extract_tables_from_query(plan.query_text)
            ))
        
        # Проблема: SELECT *
        if self._has_select_star(plan.query_text):
            recommendations.append(QueryRecommendation(
                query_hash=plan.query_hash,
                issue=QueryIssue.SELECT_STAR,
                severity='low',
                description='Query uses SELECT *',
                recommendation='Explicitly specify needed columns',
                estimated_improvement='Reduced network traffic and memory usage'
            ))
        
        # Проблема: Nested Loop на большом наборе
        if plan.has_nested_loop and plan.rows_actual > 10000:
            recommendations.append(QueryRecommendation(
                query_hash=plan.query_hash,
                issue=QueryIssue.INEFFICIENT_JOIN,
                severity='high',
                description=f'Nested Loop join on {plan.rows_actual} rows',
                recommendation='Consider Hash Join or Merge Join by adding/improving indexes',
                estimated_improvement='Significantly faster joins',
                tables_affected=self._extract_tables_from_query(plan.query_text)
            ))
        
        if recommendations:
            self._recommendations[plan.query_hash] = recommendations
            self._total_recommendations_generated += len(recommendations)
    
    def detect_n_plus_one_queries(
        self,
        query_text: str,
        timestamp: float
    ) -> bool:
        """
        Обнаружение N+1 query проблемы
        
        Args:
            query_text: Текст запроса
            timestamp: Время выполнения
            
        Returns:
            True если обнаружена N+1 проблема
        """
        if not self.detect_n_plus_one:
            return False
        
        # Создание паттерна запроса (замена литералов на плейсхолдеры)
        pattern = self._create_query_pattern(query_text)
        
        # Очистка старых записей (старше 1 минуты)
        cutoff_time = timestamp - 60
        
        if pattern in self._query_patterns:
            self._query_patterns[pattern] = [
                (t, q) for t, q in self._query_patterns[pattern]
                if t > cutoff_time
            ]
        else:
            self._query_patterns[pattern] = []
        
        # Добавление текущего запроса
        self._query_patterns[pattern].append((timestamp, query_text))
        
        # Проверка на N+1
        if len(self._query_patterns[pattern]) >= self.n_plus_one_threshold:
            self._n_plus_one_detected += 1
            
            # Создание рекомендации
            recommendation = QueryRecommendation(
                query_hash=pattern,
                issue=QueryIssue.N_PLUS_ONE,
                severity='high',
                description=f'N+1 query detected: {len(self._query_patterns[pattern])} similar queries in 1 minute',
                recommendation='Use JOIN or batch query to fetch related data',
                estimated_improvement='Reduce database roundtrips by 90%+'
            )
            
            if pattern not in self._recommendations:
                self._recommendations[pattern] = []
            self._recommendations[pattern].append(recommendation)
            
            return True
        
        return False
    
    def _create_query_pattern(self, query_text: str) -> str:
        """
        Создание паттерна запроса (замена значений на плейсхолдеры)
        
        Args:
            query_text: Текст запроса
            
        Returns:
            Паттерн запроса
        """
        # Нормализация пробелов
        pattern = re.sub(r'\s+', ' ', query_text.strip().lower())
        
        # Замена чисел на ?
        pattern = re.sub(r'\b\d+\b', '?', pattern)
        
        # Замена строковых литералов на ?
        pattern = re.sub(r"'[^']*'", '?', pattern)
        
        # Замена UUID на ?
        pattern = re.sub(
            r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            '?',
            pattern
        )
        
        return pattern
    
    def _extract_tables_from_query(self, query_text: str) -> List[str]:
        """Извлечение имен таблиц из запроса"""
        tables = []
        
        # Простое извлечение после FROM и JOIN
        from_pattern = r'(?:from|join)\s+(\w+\.?\w+)'
        matches = re.finditer(from_pattern, query_text.lower())
        
        for match in matches:
            table = match.group(1)
            if table not in tables:
                tables.append(table)
        
        return tables
    
    def _extract_where_columns(self, query_text: str) -> List[str]:
        """Извлечение колонок из WHERE clause"""
        columns = []
        
        # Поиск паттерна: column = value или column IN (...)
        where_pattern = r'where.*?(\w+\.?\w+)\s*(?:=|in|>|<|>=|<=)'
        matches = re.finditer(where_pattern, query_text.lower())
        
        for match in matches:
            column = match.group(1)
            if column not in columns and column not in ['and', 'or', 'not']:
                columns.append(column)
        
        return columns
    
    def _has_select_star(self, query_text: str) -> bool:
        """Проверка использования SELECT *"""
        return bool(re.search(r'select\s+\*', query_text.lower()))
    
    def get_recommendations_for_query(
        self,
        query_hash: str
    ) -> List[QueryRecommendation]:
        """Получение рекомендаций для запроса"""
        return self._recommendations.get(query_hash, [])
    
    def get_all_recommendations(
        self,
        severity: Optional[str] = None
    ) -> List[QueryRecommendation]:
        """
        Получение всех рекомендаций
        
        Args:
            severity: Фильтр по серьезности
            
        Returns:
            Список рекомендаций
        """
        all_recommendations = []
        
        for recommendations in self._recommendations.values():
            all_recommendations.extend(recommendations)
        
        if severity:
            all_recommendations = [
                r for r in all_recommendations if r.severity == severity
            ]
        
        return sorted(
            all_recommendations,
            key=lambda r: ['high', 'medium', 'low'].index(r.severity)
        )
    
    def get_queries_needing_indexes(self) -> List[QueryRecommendation]:
        """Получение запросов нуждающихся в индексах"""
        recommendations = self.get_all_recommendations()
        return [
            r for r in recommendations
            if r.issue == QueryIssue.MISSING_INDEX
        ]
    
    def get_n_plus_one_queries(self) -> List[QueryRecommendation]:
        """Получение N+1 queries"""
        recommendations = self.get_all_recommendations()
        return [
            r for r in recommendations
            if r.issue == QueryIssue.N_PLUS_ONE
        ]
    
    def get_metrics(self) -> Dict[str, Any]:
        """Получение метрик анализатора"""
        return {
            'enabled': self.enabled,
            'total_plans_analyzed': self._total_plans_analyzed,
            'total_recommendations': self._total_recommendations_generated,
            'n_plus_one_detected': self._n_plus_one_detected,
            'missing_indexes_detected': self._missing_indexes_detected,
            'cartesian_products_detected': self._cartesian_products_detected,
            'unique_query_patterns': len(self._query_patterns),
            'queries_with_recommendations': len(self._recommendations),
            'slow_query_threshold_ms': self.slow_query_threshold_ms
        }