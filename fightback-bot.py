import discord
from discord.ext import commands
import json
import os
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!fb ", intents=intents)

def ensure_file(filename, default):
    if not os.path.exists(filename):
        with open(filename, "w") as f:
            json.dump(default, f, indent=4)

def load_data(filename, default):
    ensure_file(filename, default)
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return default

def save_data(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)

player_data = load_data("player_data.json", {})
match_history = load_data("match_history.json", [])

def get_rank(points):
    if points >= 100:
        return "Platinum"
    elif points >= 70:
        return "Gold"
    elif points >= 40:
        return "Silver"
    else:
        return "Bronze"

def calculate_points(winner_points, loser_points, score_diff):
    rank_diff = abs(winner_points - loser_points)

    if rank_diff >= 30:
        win_bonus = 7
        lose_penalty = -3
    elif rank_diff <= 10:
        win_bonus = 5
        lose_penalty = -3
    else:
        win_bonus = 6
        lose_penalty = -4

    if score_diff == 1:
        win_bonus -= 1
        lose_penalty += 1

    return win_bonus, lose_penalty

def update_points(winner_id, loser_id, winner_score, loser_score):
    if str(winner_id) not in player_data:
        player_data[str(winner_id)] = {"name": "Unknown", "points": 0, "discord_name": ""}
    if str(loser_id) not in player_data:
        player_data[str(loser_id)] = {"name": "Unknown", "points": 0, "discord_name": ""}
    
    winner_points = player_data[str(winner_id)]["points"]
    loser_points = player_data[str(loser_id)]["points"]
    score_diff = abs(winner_score - loser_score)
    
    win_bonus, lose_penalty = calculate_points(winner_points, loser_points, score_diff)
    
    player_data[str(winner_id)]["points"] += win_bonus
    player_data[str(loser_id)]["points"] = max(0, loser_points + lose_penalty)

    save_data("player_data.json", player_data)

def revert_points(winner_id, loser_id, winner_score, loser_score):
    """Reverts the points given from a match."""
    score_diff = abs(winner_score - loser_score)
    win_bonus, lose_penalty = calculate_points(0, 0, score_diff)  # Ignore ranks for reversion

    # Remove the points given previously
    player_data[winner_id]["points"] = max(0, player_data[winner_id]["points"] - win_bonus)
    player_data[loser_id]["points"] = max(0, player_data[loser_id]["points"] - lose_penalty)


@bot.event
async def on_ready():
    print(f'✅ Logged in as {bot.user}')

@bot.command()
async def manual(ctx):
    embed = discord.Embed(title="📜 Command Manual", color=discord.Color.blue())
    embed.add_field(name="⚖️ Ranking & Points System", value="`!fb rules`", inline=False)
    embed.add_field(name="🎮 Register an Account", value="`!fb register <name>`", inline=False)
    embed.add_field(name="✏ Edit Registered Name", value="`!fb ename <new_name>`", inline=False)
    embed.add_field(name="🎮 Register a Match", value="`!fb match <W_player1> <L_player2> W_score L_score`", inline=False)
    embed.add_field(name="✏ Edit a Match", value="`!fb ematch match_number <W_player1> <L_player2> W_score L_score`", inline=False)
    embed.add_field(name="📝 Match History", value="`!fb history`", inline=False)
    embed.add_field(name="🏆 View Player Rank", value="`!fb rank [@player]`", inline=False)
    embed.add_field(name="📊 View Leaderboard", value="`!fb leaderboard`", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def rules(ctx):
    embed = discord.Embed(title="📜 Ranking & Points System", color=discord.Color.orange())

    embed.add_field(
        name="🏆 Ranks & Points Required",
        value="🔹 **Bronze**: `0 - 39 points`\n"
              "🔸 **Silver**: `40 - 69 points`\n"
              "🟡 **Gold**: `70 - 99 points`\n"
              "⚪ **Platinum**: `100+ points`\n",
        inline=False
    )

    embed.add_field(
        name="📊 Point Rewards",
        value="✅ **Winning by 1 point**: `+3 points`\n"
              "✅ **Winning by 2 points**: `+5 points`\n"
              "✅ **Winning by 3+ points**: `+6 points`\n"
              "❌ **Losing by 1 point**: `-2 points`\n"
              "❌ **Losing by 2 points**: `-3 points`\n"
              "❌ **Losing by 3+ points**: `-5 points`\n"
              "🤝 **Tie**: Both players get `+2 points`",
        inline=False
    )

    embed.add_field(
        name="📈 Defeating Higher-Ranked Opponents",
        value="🎯 **Winning against a higher-ranked player** may give an extra `+1 to +3 points` bonus!",
        inline=False
    )

    await ctx.send(embed=embed)


@bot.command()
async def register(ctx, name: str):
    if str(ctx.author.id) in player_data:
        await ctx.send("❌ You are already registered.")
        return
    player_data[str(ctx.author.id)] = {"name": name, "points": 0, "discord_name": ctx.author.name}
    save_data("player_data.json", player_data)
    await ctx.send(f"✅ {ctx.author.mention} registered as {name}!")

@bot.command()
async def ename(ctx, new_name: str):
    if str(ctx.author.id) not in player_data:
        await ctx.send("❌ You are not registered. Use `!fb register <name>` first.")
        return
    player_data[str(ctx.author.id)]["name"] = new_name
    save_data("player_data.json", player_data)
    await ctx.send(f"✅ {ctx.author.mention}, your name has been updated to {new_name}!")

@bot.command()
async def match(ctx, player1_name: str, player2_name: str, score1: int, score2: int):
    player1_id = next((id for id, data in player_data.items() if data["name"] == player1_name), None)
    player2_id = next((id for id, data in player_data.items() if data["name"] == player2_name), None)
    
    if not player1_id or not player2_id:
        await ctx.send("❌ One or both players are not registered.")
        return
    
    match_number = len(match_history) + 1
    match_entry = {
        "match_number": match_number,
        "player1": player1_id,
        "player2": player2_id,
        "score": [score1, score2]
    }
    match_history.append(match_entry)
    save_data("match_history.json", match_history)
    
    # Calculate points & get old ranks
    old_points_p1 = player_data[str(player1_id)]["points"]
    old_points_p2 = player_data[str(player2_id)]["points"]
    old_rank_p1 = get_rank(old_points_p1)
    old_rank_p2 = get_rank(old_points_p2)
    
    if score1 > score2:
        win_bonus, lose_penalty = calculate_points(old_points_p1, old_points_p2, score1 - score2)
        player_data[str(player1_id)]["points"] += win_bonus
        player_data[str(player2_id)]["points"] = max(0, old_points_p2 + lose_penalty)
    elif score2 > score1:
        win_bonus, lose_penalty = calculate_points(old_points_p2, old_points_p1, score2 - score1)
        player_data[str(player2_id)]["points"] += win_bonus
        player_data[str(player1_id)]["points"] = max(0, old_points_p1 + lose_penalty)
    else:
        player_data[str(player1_id)]["points"] += 2
        player_data[str(player2_id)]["points"] += 2
    
    save_data("player_data.json", player_data)
    
    # Get updated ranks & points
    new_points_p1 = player_data[str(player1_id)]["points"]
    new_points_p2 = player_data[str(player2_id)]["points"]
    new_rank_p1 = get_rank(new_points_p1)
    new_rank_p2 = get_rank(new_points_p2)
    
    embed = discord.Embed(title=f"🏆 Match #{match_number} Recorded!", color=discord.Color.green())
    embed.add_field(name=f"🔥 {player1_name} vs {player2_name}", value=f"**Final Score:** `{score1} - {score2}`", inline=False)
    
    embed.add_field(
        name=f"📈 {player1_name} Stats",
        value=f"**Points:** `{old_points_p1} ➡ {new_points_p1} ({'+' if new_points_p1 > old_points_p1 else ''}{new_points_p1 - old_points_p1})`\n"
              f"**Rank:** `{old_rank_p1} ➡ {new_rank_p1}`",
        inline=False
    )
    
    embed.add_field(
        name=f"📉 {player2_name} Stats",
        value=f"**Points:** `{old_points_p2} ➡ {new_points_p2} ({'+' if new_points_p2 > old_points_p2 else ''}{new_points_p2 - old_points_p2})`\n"
              f"**Rank:** `{old_rank_p2} ➡ {new_rank_p2}`",
        inline=False
    )

    await ctx.send(embed=embed)


@bot.command()
async def ematch(ctx, match_number: str, player1_name: str, player2_name: str, score1: int, score2: int):
    # Ensure match_number is an integer
    if not match_number.isdigit():
        await ctx.send("❌ Invalid match number. Please enter a valid number.")
        return
    
    match_number = int(match_number)  # Convert safely

    # Find the match by number
    match = next((m for m in match_history if m["match_number"] == match_number), None)

    if not match:
        await ctx.send("❌ Match not found.")
        return

    # Retrieve old player IDs
    old_p1_id, old_p2_id = str(match["player1"]), str(match["player2"])
    old_score1, old_score2 = match["score"]

    # Retrieve new player IDs
    new_p1_id = next((id for id, data in player_data.items() if data["name"] == player1_name), None)
    new_p2_id = next((id for id, data in player_data.items() if data["name"] == player2_name), None)

    if not new_p1_id or not new_p2_id:
        await ctx.send("❌ One or both players are not registered.")
        return

    # Revert old match points
    if old_score1 > old_score2:
        revert_points(old_p1_id, old_p2_id, old_score1, old_score2)
    elif old_score2 > old_score1:
        revert_points(old_p2_id, old_p1_id, old_score2, old_score1)
    else:
        player_data[old_p1_id]["points"] = max(0, player_data[old_p1_id]["points"] - 2)
        player_data[old_p2_id]["points"] = max(0, player_data[old_p2_id]["points"] - 2)

    # Update match record
    match["player1"], match["player2"] = new_p1_id, new_p2_id
    match["score"] = [score1, score2]

    # Apply new match results
    if score1 > score2:
        update_points(new_p1_id, new_p2_id, score1, score2)
    elif score2 > score1:
        update_points(new_p2_id, new_p1_id, score2, score1)
    else:
        player_data[new_p1_id]["points"] += 2
        player_data[new_p2_id]["points"] += 2

    save_data("match_history.json", match_history)
    save_data("player_data.json", player_data)

    await ctx.send(f"✅ Match #{match_number} updated: {player1_name} ({score1}) vs {player2_name} ({score2})")



@bot.command()
async def history(ctx):
    if not match_history:
        await ctx.send("❌ No matches recorded yet.")
        return
    
    embed = discord.Embed(title="📜 Match History (Last 10 Matches)", color=discord.Color.green())

    for match in match_history[-10:]:  # Show only the last 10 matches
        player1_id = str(match["player1"])
        player2_id = str(match["player2"])
        score1, score2 = match["score"]
        
        # Get player names
        player1_name = player_data.get(player1_id, {}).get("name", "Unknown")
        player2_name = player_data.get(player2_id, {}).get("name", "Unknown")
        
        # Get old points (before match)
        old_points_p1 = match.get("old_points_p1", 0)
        old_points_p2 = match.get("old_points_p2", 0)

        # Get new points (after match)
        new_points_p1 = player_data.get(player1_id, {}).get("points", 0)
        new_points_p2 = player_data.get(player2_id, {}).get("points", 0)

        # Calculate points gained/lost
        points_change_p1 = new_points_p1 - old_points_p1
        points_change_p2 = new_points_p2 - old_points_p2

        embed.add_field(
            name=f"Match #{match['match_number']}: {player1_name} vs {player2_name}",
            value=f"**Score:** `{score1} - {score2}`\n"
                  f"📈 `{player1_name}`: `{old_points_p1} ➡ {new_points_p1}` (`{points_change_p1:+d}` pts)\n"
                  f"📉 `{player2_name}`: `{old_points_p2} ➡ {new_points_p2}` (`{points_change_p2:+d}` pts)",
            inline=False
        )

    await ctx.send(embed=embed)


@bot.command()
async def rank(ctx, member: discord.Member = None):
    member = member or ctx.author  # Default to command sender if no member is mentioned
    player_info = player_data.get(str(member.id))

    if not player_info:
        await ctx.send(f"❌ {member.mention}, you are not registered. Use `!fb register <name>` first.")
        return
    
    points = player_info["points"]
    rank = get_rank(points)
    
    embed = discord.Embed(title="🏆 Player Rank", color=discord.Color.blue())
    embed.add_field(name="👤 Player", value=f"{member.mention} ({player_info['name']})", inline=False)
    embed.add_field(name="📊 Points", value=f"`{points}`", inline=True)
    embed.add_field(name="🏅 Rank", value=f"**{rank}**", inline=True)

    await ctx.send(embed=embed)


@bot.command()
async def leaderboard(ctx):
    if not player_data:
        await ctx.send("❌ No players have been ranked yet.")
        return

    # Sort players by points (descending) and take top 10
    sorted_players = sorted(player_data.items(), key=lambda x: x[1]["points"], reverse=True)[:10]

    # Create embed
    embed = discord.Embed(title="🏆 Leaderboard", color=discord.Color.gold())
    embed.set_thumbnail(url="https://img.icons8.com/?size=100&id=GS6HCBC44a3l&format=png&color=000000")  # Trophy Icon

    medals = ["🥇", "🥈", "🥉"]  # Top 3 players get medals

    for i, (player_id, data) in enumerate(sorted_players, 1):
        rank_icon = medals[i - 1] if i <= 3 else f"**#{i}**"
        rank = get_rank(data["points"])
        embed.add_field(
            name=f"{rank_icon} {data['name']}",
            value=f"**Points:** {data['points']} | **Rank:** {rank}",
            inline=False
        )

    embed.set_footer(text="🔥 Keep playing to climb the leaderboard!")

    await ctx.send(embed=embed)


if __name__ == "__main__":
    if BOT_TOKEN:
        bot.run(BOT_TOKEN)
    else:
        print("Error: DISCORD_BOT_TOKEN is not set in the .env file")
