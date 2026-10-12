# B站评论与弹幕生成 Skill

根据视频脚本、字幕或画面材料，生成、修改和检查中文 B站弹幕与独立主楼评论。

## 生成原则

- 根据当下已经出现的台词、动作或结果写反应，避免复述口播和提前剧透。
- 保留自然的局部重复，避免批量同义改写、机械玩梗和固定角色轮换。
- 允许少量颜文字、表情和括号语气，随情绪零散出现，不使用固定配额。
- 有时间字幕时据此对齐；只有正文时先生成候选，估算时间明确标注。
- 检查格式、数量、时间顺序、时长边界和重复分布。统计检查不能证明自然度。

## 安装

将本仓库下载或克隆为 `maintain-bilibili-comments-danmaku` 文件夹，放入 Codex 的 skills 目录。默认位置为：

- Windows：`%USERPROFILE%\.codex\skills\maintain-bilibili-comments-danmaku`
- macOS / Linux：`~/.codex/skills/maintain-bilibili-comments-danmaku`

设置了 `CODEX_HOME` 时，使用该目录下的 `skills/`。确保目标文件夹内直接包含 `SKILL.md`，不要多嵌套一层，也不要覆盖已有修改。

## 使用

提供视频脚本、字幕或画面描述，并说明需要的数量与格式。例如：

> 使用 $maintain-bilibili-comments-danmaku，根据下面的脚本生成 50 条弹幕。少复述口播，适当增加颜文字，零散分布。

未指定数量时默认先给 20 条候选。没有时长或时间码时，不凭空制造精确秒数。

## 文件

| 路径 | 用途 |
|---|---|
| `SKILL.md` | 技能入口与生成规则 |
| `agents/openai.yaml` | 技能界面描述 |
| `references/danmaku-quality.md` | 时间、表达和自然度参考 |
| `scripts/audit_bilibili_text.py` | 文本格式与分布检查，仅依赖 Python 标准库 |

## 检查时间轴

```sh
python scripts/audit_bilibili_text.py danmaku.txt --surface danmaku --duration 5:30 --expected-count 50 --strict-format
```

时间轴每行使用 `整数秒|正文`。将示例中的时长和数量替换为实际值；未知则省略相应参数。退出码 0 表示程序检查通过，1 表示没有识别到内容，2 表示检查或参数存在错误。历史格式可以宽松读取，严格模式要求标准格式。

检查评论时使用 `--surface comments`。主楼评论默认以独立一行的三位编号标记，下一行写正文，评论之间空一行。

内容生成用于草稿、编辑和选择；不包含自动发布，也不应将模拟表达当作真实用户反馈。
