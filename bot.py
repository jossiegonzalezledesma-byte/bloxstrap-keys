import discord
from discord.ext import commands
import secrets
import string
import os
import sys

sys.path.append(os.path.dirname(__file__))
from database import create_key, get_key_info, get_all_keys, reset_hwid, revoke_key
from api_server import sync_bloxstrap_config

# Configuración del Bot
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
PREFIX = "!"

if os.path.exists(CONFIG_PATH):
    try:
        import json
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            BOT_TOKEN = cfg.get("bot_token") or BOT_TOKEN
            PREFIX = cfg.get("prefix", "!")
    except Exception as e:
        print(f"[!] Error leyendo config.json: {e}")

if not BOT_TOKEN or BOT_TOKEN == "PEGA_AQUI_EL_TOKEN_DE_TU_BOT":
    BOT_TOKEN = "TU_TOKEN_AQUI"

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

def generate_key_string(prefix="SHIRO") -> str:
    chars = string.ascii_uppercase + string.digits
    p1 = ''.join(secrets.choice(chars) for _ in range(4))
    p2 = ''.join(secrets.choice(chars) for _ in range(4))
    p3 = ''.join(secrets.choice(chars) for _ in range(4))
    return f"{prefix}-{p1}-{p2}-{p3}"

@bot.event
async def on_ready():
    print(f"==================================================")
    print(f"[*] Bot de Keys conectado como: {bot.user.name}")
    print(f"[*] ID: {bot.user.id}")
    print(f"[*] Usa '{PREFIX}help' para ver los comandos")
    print(f"==================================================")
    try:
        synced = await bot.tree.sync()
        print(f"[*] Sincronizados {len(synced)} comandos Slash.")
    except Exception as e:
        print(f"[!] Error al sincronizar slash commands: {e}")

@bot.command(name="help")
async def help_cmd(ctx):
    embed = discord.Embed(
        title="🛡️ Panel de Comandos - Bot de Keys",
        description="Gestión de llaves de acceso para el Panel Secreto de Bloxstrap.",
        color=discord.Color.from_rgb(0, 255, 157)
    )
    embed.add_field(name="🔑 Generar Llave", value=f"`{PREFIX}genkey <nombre_persona>`\nCrea una nueva llave vinculada al usuario.", inline=False)
    embed.add_field(name="🔍 Consultar Información", value=f"`{PREFIX}info <nombre_o_llave>`\nMuestra el estado, HWID, usos y última conexión.", inline=False)
    embed.add_field(name="🔄 Resetear HWID", value=f"`{PREFIX}resethwid <nombre_o_llave>`\nPermite al usuario cambiar de PC liberando su HWID.", inline=False)
    embed.add_field(name="🚫 Revocar Llave", value=f"`{PREFIX}revoke <nombre_o_llave>`\nDesactiva el acceso permanentemente.", inline=False)
    embed.add_field(name="📋 Listar Todas", value=f"`{PREFIX}list`\nLista todas las llaves activas y usuarios.", inline=False)
    embed.set_footer(text="Bloxstrap Secret Panel Key Manager")
    await ctx.send(embed=embed)

@bot.command(name="genkey")
@commands.has_permissions(administrator=True)
async def genkey_cmd(ctx, username: str = None):
    if not username:
        await ctx.send("❌ **Uso:** `!genkey <nombre_persona>`")
        return

    key = generate_key_string()
    if create_key(key, username):
        sync_bloxstrap_config()
        embed = discord.Embed(
            title="🔑 Nueva Llave Generada",
            color=discord.Color.green()
        )
        embed.add_field(name="👤 Persona / Usuario", value=f"`{username}`", inline=True)
        embed.add_field(name="🎟️ Llave Asignada", value=f"```{key}```", inline=False)
        embed.add_field(name="💻 HWID", value="`No vinculado (se enlazará al primer uso)`", inline=False)
        embed.add_field(name="📊 Usos", value="`0`", inline=True)
        embed.set_footer(text="Comparte esta llave con la persona correspondiente.")
        await ctx.send(embed=embed)
    else:
        await ctx.send("❌ Error al registrar la llave en la base de datos.")

@bot.command(name="info")
async def info_cmd(ctx, identifier: str = None):
    if not identifier:
        await ctx.send("❌ **Uso:** `!info <nombre_o_llave>`")
        return

    data = get_key_info(identifier)
    if not data:
        await ctx.send("❌ No se encontró ninguna llave o usuario con ese nombre.")
        return

    status_str = "🟢 Activa" if data["is_active"] else "🔴 Desactivada/Revocada"
    hwid_str = f"```{data['hwid']}```" if data["hwid"] else "`No vinculado aún`"
    last_used_str = f"`{data['last_used']}`" if data["last_used"] else "`Nunca utilizada`"

    embed = discord.Embed(
        title=f"📋 Información de Llave: {data['username']}",
        color=discord.Color.blue()
    )
    embed.add_field(name="👤 Persona", value=f"**{data['username']}**", inline=True)
    embed.add_field(name="Estado", value=status_str, inline=True)
    embed.add_field(name="🎟️ Llave", value=f"`{data['key']}`", inline=False)
    embed.add_field(name="💻 HWID Registrado", value=hwid_str, inline=False)
    embed.add_field(name="📊 Contador de Usos", value=f"`{data['uses_count']}` veces", inline=True)
    embed.add_field(name="🕒 Último Uso", value=last_used_str, inline=True)
    embed.add_field(name="📅 Fecha de Creación", value=f"`{data['created_at']}`", inline=True)
    await ctx.send(embed=embed)

@bot.command(name="resethwid")
@commands.has_permissions(administrator=True)
async def resethwid_cmd(ctx, identifier: str = None):
    if not identifier:
        await ctx.send("❌ **Uso:** `!resethwid <nombre_o_llave>`")
        return

    if reset_hwid(identifier):
        await ctx.send(f"✅ **HWID reseteado con éxito para:** `{identifier}`. En su próximo inicio enlazará el nuevo hardware.")
    else:
        await ctx.send("❌ No se encontró el usuario o llave para resetear HWID.")

@bot.command(name="revoke")
@commands.has_permissions(administrator=True)
async def revoke_cmd(ctx, identifier: str = None):
    if not identifier:
        await ctx.send("❌ **Uso:** `!revoke <nombre_o_llave>`")
        return

    if revoke_key(identifier):
        await ctx.send(f"🚫 **Llave revocada:** `{identifier}` ya no tiene acceso al panel secreto.")
    else:
        await ctx.send("❌ No se encontró el usuario o llave a revocar.")

@bot.command(name="list")
@commands.has_permissions(administrator=True)
async def list_cmd(ctx):
    all_keys = get_all_keys()
    if not all_keys:
        await ctx.send("ℹ️ No hay llaves registradas en el sistema.")
        return

    embed = discord.Embed(
        title=f"📋 Lista de Llaves Registradas ({len(all_keys)})",
        color=discord.Color.purple()
    )
    for k in all_keys[:15]:
        hwid_badge = "🔒 Con HWID" if k["hwid"] else "🔓 Sin HWID"
        estado = "✅" if k["is_active"] else "❌"
        embed.add_field(
            name=f"{estado} {k['username']}",
            value=f"Key: `{k['key']}`\nUsos: `{k['uses_count']}` | HWID: `{hwid_badge}`\nÚltimo: `{k['last_used'] or 'Nunca'}`",
            inline=False
        )
    if len(all_keys) > 15:
        embed.set_footer(text=f"Mostrando 15 de {len(all_keys)} llaves.")
    await ctx.send(embed=embed)

if __name__ == "__main__":
    if BOT_TOKEN == "TU_TOKEN_AQUI":
        print("[!] ATENCIÓN: Debes colocar tu token de bot de Discord en BOT_TOKEN o en la variable DISCORD_BOT_TOKEN.")
    bot.run(BOT_TOKEN)
