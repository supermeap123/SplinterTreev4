import discord
from discord.ext import commands
import logging
from base_cog import BaseCog
from shared.utils import get_token_count, set_temperature

class SettingsCog(BaseCog):
    def __init__(
