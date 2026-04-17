# Bu5_ama_eu Frontend — Cockpit 主题扁平化计划

## 背景
欧洲站 EP 前端（:5180）被 iframe 嵌入到 `Amazon _cockpit` 的"加色加码"页面，URL 带 `?embed=1`。当前 `src/App.tsx` 里 `isEmbed` 已经定义，header 也用 `{!isEmbed && ...}` 包裹，但用户截图里 `AMZEU OPERATIONS DECK / AMZEU-AI 加色加码` 渐变风 hero 仍然出现，且 `rounded-2xl` 满天飞。需要彻底扁平化。

驾驶舱基调：深蓝 `#091E40` + 青绿 `#4D7B75`，**直角**、**无渐变**、**边框线为主**。

## 目标
嵌入模式下，欧洲 EP 看起来是驾驶舱的原生 part，不是外部嵌入工具。

## Token 口径
| 用途 | 颜色 |
|---|---|
| 主色 / 主按钮 | `#091E40` |
| 强调色 / 激活下划线 / 次按钮描边 | `#4D7B75` |
| 页面底 | `#F7F9FA` |
| 分割线 / 边框 | `#E8EAED` |
| 正文 | `#091E40` |
| 次要文字 | `#8C8C8C` |
| 危险 | `#D14343` |

tailwind.config.js 里的 token：`ink=#091E40`、`aurora=#4D7B75`、`pine=#4D7B75`、`mist=#F7F9FA`、`steel=#6B7280`。可以继续用。

## 必做项

### 1. `src/App.tsx` — header 门禁 + 确认生效
- 把 `isEmbed` 的计算移到 `App()` 顶部第一行，保证每次 render 都拿到当前 URL 参数（当前位置已经可以，但建议顺便检查没有在条件分支里被旁路）。
- `{!isEmbed && (<header ...>)}` 保持不变，但确认包裹范围是**整个 header 元素**，不是 header 内部某个子节点。
- 用户截图里 hero 还出现 → 大概率是 Vite dev server 没热更到。在 `src/App.tsx` 结尾加个无意义注释（`// cockpit-theme-v1`）强制 HMR；如果仍有问题，杀掉 5180 端口的 dev server 进程重启：
  ```bash
  lsof -ti:5180 | xargs kill -9 2>/dev/null; cd frontend && npm run dev -- --port 5180 &
  ```
- Tab 栏（加色加码 / 颜色映射管理 / 跟卖上新 / 下载历史）从现在的 `border-b-2 border-aurora` 已经接近下划线样式，但激活态没有足够区分。调整为：
  - 激活：`border-b-2 border-[#4D7B75] text-[#091E40] font-semibold`
  - 未激活：`border-b-2 border-transparent text-[#8C8C8C] hover:text-[#091E40]`
  - 父容器加 `border-b border-[#E8EAED]`

### 2. 国家选择卡片 `src/components/CountrySelector/CountrySelector.tsx`
- 当前 UK/FR/DE/IT/ES 是大 `rounded-2xl` 卡片 + 柔光背景 → 改成：
  - 外层容器：`border border-[#E8EAED] bg-white`（直角，无阴影）
  - 激活国家：加 `border-l-4 border-l-[#4D7B75]` + `bg-[rgba(77,123,117,0.05)]`
  - hover：`hover:bg-[#F7F9FA]`
  - 旗帜图标保留，文字颜色改成 `#091E40` 主 / `#8C8C8C` 次
  - 国家简写徽章（UK/FR/…）：`bg-[#091E40] text-white px-2 py-0.5 text-xs font-bold`（直角）

### 3. 全局扫描 `src/` 下所有 `.tsx/.ts`
去掉或替换：
- **全部** `rounded-2xl / rounded-xl / rounded-lg / rounded-md`（例外：`rounded-full` 仅保留给头像、状态圆点）
- `shadow-lg / shadow-xl / shadow-2xl` → `shadow-sm` 或删掉
- `bg-gradient-* / from-* / to-* / via-*` 整条链替换成纯色
- 任何 `bg-slate-*` → `bg-[#F7F9FA]` 或 `bg-white`
- `border-slate-*` → `border-[#E8EAED]`
- `text-slate-*`（muted）→ `text-[#8C8C8C]`
- 错误态 `bg-red-50 text-red-700 border-red-200` → `bg-[#FEF2F2] text-[#D14343] border-[#D14343]`（直角）
- 警告态 `bg-amber-50 text-amber-700 border-amber-200` → `bg-[#FFF7E6] text-[#D46B08] border-[#E8B84B]`（直角）

### 4. 按钮标准化
- 主按钮：`bg-[#091E40] text-white px-4 py-2 text-sm hover:bg-[#0D2B52]`
- 次按钮：`bg-white text-[#091E40] border border-[#E8EAED] px-4 py-2 text-sm hover:bg-[#F7F9FA]`
- 青绿次要 CTA：`bg-[rgba(77,123,117,0.08)] text-[#4D7B75] border border-[#4D7B75] px-4 py-2 text-sm`

## 不要做的事
- 不要改任何 backend Python 代码
- 不要改业务逻辑（API、store、router、表单提交）
- 不要改 `tailwind.config.js` 的 token 名（保持 `ink/aurora/pine/mist` 继续可用）
- 不要动 backend、tests、config、docs

## 验证
1. `cd frontend && npm run build`，无报错
2. 重启 5180 dev server：`lsof -ti:5180 | xargs kill -9 2>/dev/null; npm run dev -- --port 5180 &`
3. 浏览器打开 `http://localhost:5180/?embed=1`，确认：
   - 完全看不到 `AMZEU OPERATIONS DECK` hero
   - 无大圆角卡片
   - 国家选择卡片是直角边框风
   - Tabs 下划线风
   - 无任何大阴影或渐变
4. 打开 `http://localhost:5180/`（不带 embed），header 正常显示（非嵌入模式保留原样标题）

## 提交
完成后：
```bash
cd ~/PycharmProjects/Bu5_ama_eu
git add frontend
git commit -m "style(bu5): flatten EU-EP theme to cockpit baseline"
```
**不要 push**。
