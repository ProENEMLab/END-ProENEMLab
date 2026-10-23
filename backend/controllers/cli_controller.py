import json

import click

@click.command("seed")
def seed_command() -> None:
    from services.seed_service import run_seed

    run_seed()
    print("Seed completed.")

@click.command("sync-enem")
@click.option("--year", type=int, default=None, help="Sincronizar um ano específico")
@click.option("--all-years", is_flag=True, help="Sincronizar todas as provas disponíveis")
def sync_enem_command(year, all_years) -> None:
    from container import enem_service

    click.echo(enem_service.sync_exams(year=year, all_years=all_years))

@click.command("add-testimonial")
@click.option("--name", required=True, help="Nome ou iniciais exibidos")
@click.option("--quote", required=True, help="Citação curta")
@click.option(
    "--result", required=True, help="Resultado específico (ex.: concluiu o roadmap de Matemática)"
)
@click.option("--avatar", default=None, help="URL de foto (opcional)")
@click.option("--consent/--no-consent", default=False, help="Consentimento registrado do citado")
@click.option("--publish/--no-publish", default=False, help="Publicar na landing (exige --consent)")
def add_testimonial_command(name, quote, result, avatar, consent, publish) -> None:
    from container import testimonials_service

    item = testimonials_service.add_testimonial(
        name,
        quote,
        result,
        avatar_url=avatar,
        consent=consent,
        publish=publish,
    )
    click.echo(item)

@click.command("refresh-incidence")
@click.option("--force", is_flag=True, help="Recalcula mesmo se este ano já foi atualizado")
def refresh_incidence_command(force: bool) -> None:
    from container import incidence_service as service

    click.echo(service.refresh(force=force)["refresh"])

@click.group("inep")
def inep_group() -> None:
    pass

@inep_group.command("import-items")
@click.option("--year", type=int, required=True, help="Edição do ENEM")
@click.option(
    "--file", "file_path", default=None, help="CSV ITENS_PROVA, se não estiver na pasta padrão"
)
def import_items_command(year: int, file_path: str | None) -> None:
    from container import inep_import_service

    click.echo(json.dumps(inep_import_service.import_items(year, file_path), ensure_ascii=False))

@inep_group.command("link-questions")
@click.option("--year", type=int, default=None, help="Limita o casamento a uma edição")
def link_questions_command(year: int | None) -> None:
    from container import inep_import_service

    click.echo(json.dumps(inep_import_service.link_questions(year), ensure_ascii=False))

@click.group("difficulty")
def difficulty_group() -> None:
    pass

@difficulty_group.command("recompute")
def recompute_difficulty_command() -> None:
    from container import inep_import_service

    click.echo(json.dumps(inep_import_service.recompute(), ensure_ascii=False))

@click.group("reports")
def reports_group() -> None:
    pass

@reports_group.command("rebuild")
@click.option("--user", "user_id", type=int, required=True, help="Id do usuário")
@click.option("--week", required=True, help="Segunda-feira da semana, YYYY-MM-DD")
def rebuild_report_command(user_id: int, week: str) -> None:
    from datetime import datetime

    from container import report_service
    from services.exceptions import ApiError

    try:
        day = datetime.strptime(week, "%Y-%m-%d").date()
    except ValueError as exc:
        raise click.ClickException("week tem que ser YYYY-MM-DD.") from exc
    try:
        payload = report_service.rebuild(user_id, day)
    except ApiError as err:
        raise click.ClickException(err.message) from err
    click.echo(json.dumps(payload, ensure_ascii=False))

@click.group("notifications")
def notifications_group() -> None:
    pass

@notifications_group.command("dispatch")
def dispatch_notifications_command() -> None:
    from container import dispatcher_service

    click.echo(json.dumps(dispatcher_service.dispatch(), ensure_ascii=False))

@notifications_group.command("generate-vapid")
def generate_vapid_command() -> None:
    from services.notifications.channels.vapid import generate_vapid_pair

    public, private = generate_vapid_pair()
    pem = private.strip().replace("\n", "\\n")
    click.echo("Cole estas linhas no .env do backend. Não commite a chave privada.")
    click.echo(f"VAPID_PUBLIC_KEY={public}")
    click.echo(f'VAPID_PRIVATE_KEY="{pem}"')
    click.echo("VAPID_SUBJECT=mailto:voce@exemplo.com")

def _echo_json(payload) -> None:
    click.echo(json.dumps(payload, ensure_ascii=False))

def _format_diff(report: dict) -> str:
    lines = [f"Rascunho {report['draft_id']} comparado com a versão ativa {report['active_id']}."]
    if report["active_id"] is None:
        lines[0] = f"Rascunho {report['draft_id']} comparado com a ordem atual do roadmap."
    coverage = ", ".join(f"{year}={value}" for year, value in report["coverage"].items())
    lines.append(f"Cobertura: {coverage}.")
    if report["moved"]:
        lines.append("Tópicos que subiram ou desceram 5 ou mais posições:")
        for item in report["moved"]:
            direction = "subiu" if item["delta"] < 0 else "desceu"
            lines.append(f"- {item['name']}: {item['from']} → {item['to']} ({direction})")
    else:
        lines.append("Nenhum tópico mudou 5 ou mais posições.")
    if report["new_low_incidence"]:
        lines.append("Novos tópicos com incidência baixa:")
        for item in report["new_low_incidence"]:
            lines.append(f"- {item['name']}")
    else:
        lines.append("Nenhum tópico novo com incidência baixa.")
    if report["below_minimum"]:
        lines.append(
            "A cobertura está abaixo do mínimo "
            f"({report['minimum_coverage']}). A ativação exige --allow-low-coverage."
        )
    return "\n".join(lines)

@click.group("roadmap")
def roadmap_group() -> None:
    pass

@roadmap_group.command("build")
@click.option("--reference-year", type=int, required=True, help="Ano de referência do arquivo")
@click.option("--data-dir", default=None, help="Pasta dos arquivos, se não for a padrão")
def roadmap_build_command(reference_year: int, data_dir: str | None) -> None:
    from container import roadmap_version_service
    from services.roadmap_catalog import RoadmapDataError

    try:
        payload = roadmap_version_service.build(reference_year, data_dir=data_dir)
    except RoadmapDataError as err:
        raise click.ClickException(str(err)) from err
    _echo_json(payload)

@roadmap_group.command("diff")
@click.argument("draft_id", type=int)
def roadmap_diff_command(draft_id: int) -> None:
    from container import roadmap_version_service
    from services.roadmap_catalog import RoadmapDataError

    try:
        report = roadmap_version_service.diff(draft_id)
    except RoadmapDataError as err:
        raise click.ClickException(str(err)) from err
    click.echo(_format_diff(report))

@roadmap_group.command("activate")
@click.argument("draft_id", type=int)
@click.option(
    "--allow-low-coverage", is_flag=True, help="Ativa mesmo com cobertura abaixo do mínimo"
)
def roadmap_activate_command(draft_id: int, allow_low_coverage: bool) -> None:
    from container import roadmap_version_service
    from services.roadmap_catalog import RoadmapDataError

    try:
        payload = roadmap_version_service.activate(draft_id, allow_low_coverage=allow_low_coverage)
    except RoadmapDataError as err:
        raise click.ClickException(str(err)) from err
    _echo_json(payload)

@roadmap_group.command("list")
def roadmap_list_command() -> None:
    from container import roadmap_version_service

    _echo_json(roadmap_version_service.list_versions())

@roadmap_group.command("scheduled-build")
@click.option("--data-dir", default=None, help="Pasta dos arquivos, se não for a padrão")
def roadmap_scheduled_build_command(data_dir: str | None) -> None:
    from container import roadmap_version_service
    from services.roadmap_catalog import RoadmapDataError

    try:
        payload = roadmap_version_service.scheduled_build(data_dir=data_dir)
    except RoadmapDataError as err:
        raise click.ClickException(str(err)) from err
    click.echo(
        f"Rascunho {payload['id']} gerado para {payload['reference_year']}. Não foi ativado."
    )
    _echo_json(payload)
