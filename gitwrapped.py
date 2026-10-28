#!/usr/bin/env python3
"""
gitwrapped - o "Spotify Wrapped" do seu repositório Git, direto no terminal.

Zero dependências. Só Python 3.8+ e git.

Uso:
    python gitwrapped.py                      # repo da pasta atual
    python gitwrapped.py ~/projetos/meu-repo
    python gitwrapped.py --since 2026-01-01
    python gitwrapped.py --author "Maria"
"""
import argparse
import collections
import datetime as dt
import re
import subprocess
import sys

DIAS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
SHADES = [240, 22, 28, 34, 40, 46]  # cinza -> verde (ansi 256)
STOPWORDS = {
    "with", "from", "that", "this", "para", "pelo", "pela", "como", "mais",
    "into", "when", "have", "uses", "using", "add", "fix", "feat", "chore",
    "update", "merge", "branch", "files", "file", "the", "and", "for",
}

USE_COLOR = sys.stdout.isatty()


def c(text, code):
    return f"\033[38;5;{code}m{text}\033[0m" if USE_COLOR else str(text)


def bold(text):
    return f"\033[1m{text}\033[0m" if USE_COLOR else str(text)


def git(repo, *args):
    r = subprocess.run(
        ["git", "-C", repo, *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if r.returncode != 0:
        sys.exit(f"Erro: {r.stderr.strip() or 'não é um repositório git'}")
    return r.stdout


def filtros(args):
    f = []
    if args.since:
        f.append(f"--since={args.since}")
    if args.author:
        f.append(f"--author={args.author}")
    return f


def carregar_commits(repo, args):
    saida = git(repo, "log", "--no-merges", "--pretty=format:%an|%aI|%s", *filtros(args))
    commits = []
    for linha in saida.splitlines():
        try:
            autor, data, msg = linha.split("|", 2)
            commits.append((autor, dt.datetime.fromisoformat(data), msg))
        except ValueError:
            continue
    return commits


def carregar_arquivos(repo, args):
    saida = git(repo, "log", "--no-merges", "--numstat", "--pretty=format:", *filtros(args))
    cont = collections.Counter()
    for linha in saida.splitlines():
        partes = linha.split("\t")
        if len(partes) == 3:
            add, rem, caminho = partes
            if add.isdigit() and rem.isdigit():
                cont[caminho] += int(add) + int(rem)
    return cont


def maior_streak(datas):
    ordenadas = sorted(set(datas))
    melhor = atual = 1 if ordenadas else 0
    for a, b in zip(ordenadas, ordenadas[1:]):
        atual = atual + 1 if (b - a).days == 1 else 1
        melhor = max(melhor, atual)
    return melhor


def persona(horas, dias_semana):
    total = sum(horas.values()) or 1
    madrugada = sum(horas[h] for h in range(0, 5)) / total
    manha = sum(horas[h] for h in range(5, 10)) / total
    comercial = sum(horas[h] for h in range(9, 18)) / total
    fds = sum(dias_semana[d] for d in (5, 6)) / total
    if madrugada > 0.25:
        return "🦉 Coruja Noturna", "seus melhores commits nascem depois da meia-noite."
    if fds > 0.35:
        return "🏴‍☠️ Guerreiro de Fim de Semana", "o repo cresce quando os outros descansam."
    if manha > 0.30:
        return "🐓 Madrugador", "café, terminal e commit antes das 9h."
    if comercial > 0.60:
        return "👔 Profissional das 9 às 18", "disciplina de CLT, código de alta qualidade."
    return "🌀 Caótico Neutro", "commita a qualquer hora, sem piedade."


def barra(v, mx, largura=28):
    return "█" * (round(v / mx * largura) if mx else 0)


def titulo(texto):
    print("\n" + bold(c(f"▌ {texto}", 214)))


def heatmap(grade):
    mx = max((v for linha in grade for v in linha), default=0) or 1
    print("      " + "".join(f"{h:<3d}"[:3] if h % 3 == 0 else "   " for h in range(24)))
    for i, linha in enumerate(grade):
        celulas = ""
        for v in linha:
            nivel = 0 if v == 0 else 1 + int(v / mx * (len(SHADES) - 2))
            celulas += c("■", SHADES[min(nivel, len(SHADES) - 1)]) + "  "
        print(f" {DIAS[i]}  {celulas}")


def main():
    p = argparse.ArgumentParser(description="O Spotify Wrapped do seu repo Git.")
    p.add_argument("repo", nargs="?", default=".", help="caminho do repositório")
    p.add_argument("--since", help="ex: 2026-01-01 ou '6 months ago'")
    p.add_argument("--author", help="filtra por autor")
    args = p.parse_args()

    commits = carregar_commits(args.repo, args)
    if not commits:
        sys.exit("Nenhum commit encontrado com esses filtros.")

    datas = [d.date() for _, d, _ in commits]
    horas = collections.Counter(d.hour for _, d, _ in commits)
    dias_semana = collections.Counter(d.weekday() for _, d, _ in commits)
    grade = [[0] * 24 for _ in range(7)]
    for _, d, _ in commits:
        grade[d.weekday()][d.hour] += 1

    print(bold(c("\n  ╔═══════════════════════════════╗", 214)))
    print(bold(c("  ║        G I T   W R A P P E D  ║", 214)))
    print(bold(c("  ╚═══════════════════════════════╝", 214)))

    titulo("Visão geral")
    dias_ativos = len(set(datas))
    print(f"  Commits ............ {bold(len(commits))}")
    print(f"  Dias ativos ........ {bold(dias_ativos)}")
    print(f"  Primeiro commit .... {min(datas)}")
    print(f"  Último commit ...... {max(datas)}")
    print(f"  Maior sequência .... {bold(maior_streak(datas))} dias seguidos 🔥")
    dia_top, qtd_top = collections.Counter(datas).most_common(1)[0]
    print(f"  Dia mais insano .... {dia_top} ({qtd_top} commits)")

    nome, desc = persona(horas, dias_semana)
    titulo("Sua persona")
    print(f"  {bold(nome)}")
    print(f"  {desc}")

    titulo("Mapa de calor (dia da semana × hora)")
    heatmap(grade)

    titulo("Commits por hora")
    mx = max(horas.values())
    for h in range(24):
        if horas[h]:
            print(f"  {h:02d}h {c(barra(horas[h], mx), 40)} {horas[h]}")

    titulo("Top contribuidores")
    autores = collections.Counter(a for a, _, _ in commits)
    mx = autores.most_common(1)[0][1]
    for a, n in autores.most_common(5):
        print(f"  {a[:20]:<20} {c(barra(n, mx, 20), 39)} {n}")

    titulo("Arquivos mais mexidos (linhas +/-)")
    for caminho, n in carregar_arquivos(args.repo, args).most_common(5):
        print(f"  {n:>6}  {caminho}")

    titulo("Tipos de commit (Conventional Commits)")
    tipos = collections.Counter()
    for _, _, msg in commits:
        m = re.match(r"^(\w+)(\(.+?\))?!?:", msg)
        if m:
            tipos[m.group(1).lower()] += 1
    if tipos:
        for t, n in tipos.most_common(5):
            print(f"  {t:<10} {n}")
    else:
        print("  (nenhum padrão feat:/fix: encontrado)")

    titulo("Palavras favoritas nas mensagens")
    palavras = collections.Counter()
    for _, _, msg in commits:
        for w in re.findall(r"[a-zA-ZÀ-ÿ]{4,}", msg.lower()):
            if w not in STOPWORDS:
                palavras[w] += 1
    print("  " + "  ".join(f"{w} ({n})" for w, n in palavras.most_common(6)))

    print(c("\n  Gostou? Deixe uma ⭐ no repo!\n", 244))


if __name__ == "__main__":
    main()
