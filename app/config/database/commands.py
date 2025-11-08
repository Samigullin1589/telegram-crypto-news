"""
CLI команды для управления оптимизацией БД

Предоставляет командный интерфейс для:
- Запуска оптимизации
- Просмотра статуса
- Управления компонентами
- Генерации отчетов
"""

import asyncio
import sys
from typing import Optional
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from . import DatabaseManager, get_db_manager
from .utils import bytes_to_human_readable, format_duration


console = Console()


@click.group()
def database_cli():
    """Database optimization and management CLI"""
    pass


@database_cli.command()
@click.option('--full', is_flag=True, help='Run full optimization cycle')
@click.option('--component', type=str, help='Optimize specific component only')
async def optimize(full: bool, component: Optional[str]):
    """Run database optimization"""
    console.print("\n[bold blue]Starting database optimization...[/bold blue]\n")
    
    try:
        db_manager = get_db_manager()
        
        # Инициализация если нужно
        if not db_manager._initialized:
            console.print("[yellow]Initializing database manager...[/yellow]")
            init_result = await db_manager.initialize()
            console.print(f"[green]✓[/green] Initialized: {init_result['status']}\n")
        
        # Запуск оптимизации
        with console.status("[bold green]Running optimization cycle..."):
            result = await db_manager.run_optimization()
        
        # Вывод результатов
        if result['status'] == 'completed':
            console.print(f"\n[bold green]✓ Optimization completed[/bold green]")
            console.print(f"Duration: {format_duration(result['duration_seconds'])}")
            console.print(f"Operations executed: {result['operations_executed']}")
            console.print(f"Operations failed: {result['operations_failed']}")
            
            # Таблица с фазами
            table = Table(title="Optimization Phases", box=box.ROUNDED)
            table.add_column("Phase", style="cyan")
            table.add_column("Status", style="green")
            table.add_column("Details")
            
            for phase_name, phase_data in result.get('phases', {}).items():
                status = "✓" if isinstance(phase_data, dict) else "?"
                details = str(phase_data.get('phase', '')) if isinstance(phase_data, dict) else ""
                table.add_row(phase_name, status, details)
            
            console.print(table)
        
        elif result['status'] == 'deferred_due_to_load':
            console.print(f"\n[yellow]⚠ Optimization deferred due to high load[/yellow]")
            console.print(f"Current load: {result['current_load_percent']:.1f}%")
        
        else:
            console.print(f"\n[red]✗ Optimization failed[/red]")
            if 'error' in result:
                console.print(f"Error: {result['error']}")
    
    except Exception as e:
        console.print(f"\n[red]✗ Error: {str(e)}[/red]")
        sys.exit(1)


@database_cli.command()
@click.option('--format', type=click.Choice(['table', 'json']), default='table')
def status(format: str):
    """Show database optimization status"""
    try:
        db_manager = get_db_manager()
        status_data = db_manager.get_status()
        
        if format == 'json':
            import json
            console.print_json(json.dumps(status_data, indent=2))
            return
        
        # Таблица со статусом
        console.print("\n[bold]Database Optimization Status[/bold]\n")
        
        # Общая информация
        info_table = Table(box=box.SIMPLE)
        info_table.add_column("Property", style="cyan")
        info_table.add_column("Value")
        
        info_table.add_row("Initialized", "✓" if status_data['initialized'] else "✗")
        info_table.add_row("Database", status_data['config']['database'])
        info_table.add_row("Host", f"{status_data['config']['host']}:{status_data['config']['port']}")
        info_table.add_row("Health", status_data.get('health', 'unknown').upper())
        
        console.print(info_table)
        
        # Компоненты
        if status_data['optimizer']:
            console.print("\n[bold]Components Status[/bold]\n")
            
            components_table = Table(box=box.ROUNDED)
            components_table.add_column("Component", style="cyan")
            components_table.add_column("Enabled")
            components_table.add_column("Metrics")
            
            for comp_name, comp_data in status_data['optimizer']['components'].items():
                enabled = "✓" if comp_data.get('enabled', False) else "✗"
                metrics = f"{len(comp_data)} metrics"
                components_table.add_row(comp_name, enabled, metrics)
            
            console.print(components_table)
    
    except Exception as e:
        console.print(f"\n[red]✗ Error: {str(e)}[/red]")
        sys.exit(1)


@database_cli.command()
@click.option('--component', type=str, help='Show metrics for specific component')
@click.option('--format', type=click.Choice(['table', 'json']), default='table')
def metrics(component: Optional[str], format: str):
    """Show database metrics"""
    try:
        db_manager = get_db_manager()
        metrics_data = db_manager.get_metrics()
        
        if format == 'json':
            import json
            if component:
                console.print_json(json.dumps(metrics_data.get(component, {}), indent=2))
            else:
                console.print_json(json.dumps(metrics_data, indent=2))
            return
        
        if component:
            # Показать метрики одного компонента
            comp_metrics = metrics_data.get(component, {})
            
            console.print(f"\n[bold]{component.upper()} Metrics[/bold]\n")
            
            table = Table(box=box.ROUNDED)
            table.add_column("Metric", style="cyan")
            table.add_column("Value")
            
            for key, value in comp_metrics.items():
                if isinstance(value, float):
                    value_str = f"{value:.2f}"
                elif isinstance(value, bool):
                    value_str = "✓" if value else "✗"
                else:
                    value_str = str(value)
                
                table.add_row(key, value_str)
            
            console.print(table)
        
        else:
            # Показать сводку по всем компонентам
            console.print("\n[bold]Database Metrics Summary[/bold]\n")
            
            for comp_name, comp_metrics in metrics_data.items():
                panel_content = []
                
                # Выбираем ключевые метрики
                key_metrics = {}
                if comp_name == 'pool':
                    key_metrics = {
                        'Total Connections': comp_metrics.get('total_current', 0),
                        'Utilization': f"{comp_metrics.get('utilization_percent', 0):.1f}%",
                        'Active': comp_metrics.get('current_active', 0)
                    }
                elif comp_name == 'cache':
                    key_metrics = {
                        'Hit Rate': f"{comp_metrics.get('hit_rate_percent', 0):.1f}%",
                        'Size': bytes_to_human_readable(int(comp_metrics.get('memory_size_mb', 0) * 1024 * 1024)),
                        'Entries': comp_metrics.get('memory_entries_count', 0)
                    }
                elif comp_name == 'vacuum':
                    key_metrics = {
                        'Total Operations': comp_metrics.get('total_operations', 0),
                        'Success Rate': f"{comp_metrics.get('successful_operations', 0)}/{comp_metrics.get('total_operations', 0)}",
                        'Active': comp_metrics.get('active_operations', 0)
                    }
                
                for metric_name, metric_value in key_metrics.items():
                    panel_content.append(f"{metric_name}: [bold]{metric_value}[/bold]")
                
                if panel_content:
                    console.print(Panel(
                        "\n".join(panel_content),
                        title=f"[cyan]{comp_name.upper()}[/cyan]",
                        box=box.ROUNDED
                    ))
    
    except Exception as e:
        console.print(f"\n[red]✗ Error: {str(e)}[/red]")
        sys.exit(1)


@database_cli.command()
@click.option('--severity', type=click.Choice(['high', 'medium', 'low']), help='Filter by severity')
def recommendations(severity: Optional[str]):
    """Show optimization recommendations"""
    try:
        db_manager = get_db_manager()
        recs = db_manager.get_recommendations(severity)
        
        console.print("\n[bold]Optimization Recommendations[/bold]\n")
        
        total_recs = sum(
            len(r) if isinstance(r, list) else 1
            for r in recs.values()
        )
        
        if total_recs == 0:
            console.print("[green]No recommendations at this time. System is optimized![/green]")
            return
        
        # Индексы
        if recs.get('indexes'):
            console.print("[bold cyan]Indexes:[/bold cyan]")
            for rec in recs['indexes'][:5]:  # Top 5
                icon = "🔴" if rec.severity == 'high' else "🟡" if rec.severity == 'medium' else "🟢"
                console.print(f"{icon} {rec.description}")
                console.print(f"   → {rec.recommendation}")
                console.print(f"   Impact: {rec.estimated_improvement}\n")
        
        # Запросы
        if recs.get('queries'):
            console.print("[bold cyan]Queries:[/bold cyan]")
            for rec in recs['queries'][:5]:  # Top 5
                icon = "🔴" if rec.severity == 'high' else "🟡" if rec.severity == 'medium' else "🟢"
                console.print(f"{icon} {rec.description}")
                console.print(f"   → {rec.recommendation}\n")
        
        # VACUUM
        if recs.get('vacuum'):
            console.print(f"[bold cyan]VACUUM:[/bold cyan] {len(recs['vacuum'])} tables need attention\n")
        
        # Партиции
        if recs.get('partitions'):
            part_data = recs['partitions']
            console.print(f"[bold cyan]Partitions:[/bold cyan]")
            console.print(f"   • {part_data.get('expired_to_drop', 0)} expired partitions to drop")
            console.print(f"   • {part_data.get('new_to_create', 0)} new partitions to create\n")
    
    except Exception as e:
        console.print(f"\n[red]✗ Error: {str(e)}[/red]")
        sys.exit(1)


@database_cli.command()
@click.option('--active-only', is_flag=True, help='Show only active alerts')
def alerts(active_only: bool):
    """Show database alerts"""
    try:
        db_manager = get_db_manager()
        alerts_data = db_manager.get_alerts(active_only)
        
        console.print("\n[bold]Database Alerts[/bold]\n")
        
        if alerts_data['total'] == 0:
            console.print("[green]No alerts! System is healthy.[/green]")
            return
        
        # Сводка
        console.print(f"Total: {alerts_data['total']}")
        console.print(f"Critical: [red]{alerts_data['critical']}[/red]")
        console.print(f"Warning: [yellow]{alerts_data['warning']}[/yellow]\n")
        
        # Таблица с алертами
        table = Table(box=box.ROUNDED)
        table.add_column("Severity", style="bold")
        table.add_column("Metric")
        table.add_column("Message")
        table.add_column("Duration")
        
        for alert in alerts_data['alerts'][:10]:  # Top 10
            severity_color = "red" if alert['severity'] == 'critical' else "yellow"
            severity = f"[{severity_color}]{alert['severity'].upper()}[/{severity_color}]"
            duration = format_duration(alert['duration_seconds'])
            
            table.add_row(
                severity,
                alert['metric'],
                alert['message'][:50] + "..." if len(alert['message']) > 50 else alert['message'],
                duration
            )
        
        console.print(table)
    
    except Exception as e:
        console.print(f"\n[red]✗ Error: {str(e)}[/red]")
        sys.exit(1)


@database_cli.command()
@click.option('--output', type=click.Path(), help='Output file path')
def report(output: Optional[str]):
    """Generate optimization report"""
    try:
        db_manager = get_db_manager()
        
        console.print("\n[bold blue]Generating optimization report...[/bold blue]\n")
        
        # Сбор данных
        status = db_manager.get_status()
        metrics = db_manager.get_metrics()
        recs = db_manager.get_recommendations()
        alerts_data = db_manager.get_alerts(active_only=False)
        
        # Генерация Markdown отчета
        from .utils import generate_markdown_report
        from datetime import datetime
        
        report_sections = {
            'Overview': {
                'Generated At': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'Database': status['config']['database'],
                'Health Status': status.get('health', 'unknown').upper(),
                'Optimization Enabled': status['optimizer'] is not None
            },
            'Components Status': {},
            'Metrics Summary': {},
            'Recommendations': {
                'Total Recommendations': sum(len(r) if isinstance(r, list) else 1 for r in recs.values())
            },
            'Alerts': {
                'Total Alerts': alerts_data['total'],
                'Critical': alerts_data['critical'],
                'Warning': alerts_data['warning']
            }
        }
        
        # Добавление статуса компонентов
        if status['optimizer']:
            for comp_name, comp_data in status['optimizer']['components'].items():
                report_sections['Components Status'][comp_name] = {
                    'Enabled': comp_data.get('enabled', False),
                    'Metrics Count': len(comp_data)
                }
        
        # Добавление ключевых метрик
        for comp_name, comp_metrics in metrics.items():
            if comp_name == 'cache':
                report_sections['Metrics Summary'][f'{comp_name} Hit Rate'] = f"{comp_metrics.get('hit_rate_percent', 0):.1f}%"
            elif comp_name == 'pool':
                report_sections['Metrics Summary'][f'{comp_name} Utilization'] = f"{comp_metrics.get('utilization_percent', 0):.1f}%"
        
        report_md = generate_markdown_report(
            'Database Optimization Report',
            report_sections
        )
        
        if output:
            with open(output, 'w') as f:
                f.write(report_md)
            console.print(f"[green]✓ Report saved to: {output}[/green]")
        else:
            console.print(report_md)
    
    except Exception as e:
        console.print(f"\n[red]✗ Error: {str(e)}[/red]")
        sys.exit(1)


@database_cli.command()
@click.confirmation_option(prompt='Are you sure you want to shutdown the optimizer?')
async def shutdown():
    """Shutdown database optimizer"""
    try:
        db_manager = get_db_manager()
        
        console.print("\n[yellow]Shutting down database optimizer...[/yellow]\n")
        
        result = await db_manager.shutdown()
        
        console.print(f"[green]✓ Shutdown complete: {result['status']}[/green]")
    
    except Exception as e:
        console.print(f"\n[red]✗ Error: {str(e)}[/red]")
        sys.exit(1)


# Wrapper для async команд
def async_command(f):
    """Decorator для async click команд"""
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapper


# Применение decorator к async командам
optimize.callback = async_command(optimize.callback)
shutdown.callback = async_command(shutdown.callback)


if __name__ == '__main__':
    database_cli()