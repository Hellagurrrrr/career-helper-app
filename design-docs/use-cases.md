# Demo 功能用例（Use Cases）

> 本文档按页面整理 demo 的功能用例，每个页面一个独立表格；同一功能可包含多个用例。
> 注：本应用为纯前端 demo，所有数据保存在浏览器 `localStorage`，无后端。

---

## 1. 登录页 `/login`


| 功能   | 用例编号     | 用例名称               | 前置条件                 | 操作步骤                     | 预期结果                                        |
| ---- | -------- | ------------------ | -------------------- | ------------------------ | ------------------------------------------- |
| 邮箱登录 | LOGIN-01 | 已有 profile 的账号登录成功 | 已注册账号且已完成 onboarding | 输入正确邮箱和密码，点击 Sign in     | 登录成功，跳转 Dashboard `/`                       |
| 邮箱登录 | LOGIN-02 | 无 profile 的账号登录成功  | 已注册账号但未完成 onboarding | 输入正确邮箱和密码，点击 Sign in     | 登录成功，跳转 `/onboarding`                       |
| 邮箱登录 | LOGIN-03 | 邮箱不存在              | 该邮箱未注册               | 输入未注册邮箱，点击 Sign in       | 显示红色错误提示 "No account found for this email." |
| 邮箱登录 | LOGIN-04 | 密码错误               | 已注册账号                | 输入正确邮箱 + 错误密码，点击 Sign in | 显示红色错误提示 "Incorrect password."              |
| 邮箱登录 | LOGIN-05 | 邮箱大小写/空格容错         | 已注册账号                | 输入带前后空格、含大写字母的邮箱         | 邮箱被 trim 并转小写后匹配，登录成功                       |
| 注册入口 | LOGIN-06 | 跳转注册页              | 处于登录页                | 点击页脚注册链接                 | 跳转 `/register`                              |


---

## 2. 注册页 `/register`


| 功能   | 用例编号   | 用例名称  | 前置条件   | 操作步骤                                     | 预期结果                                            |
| ---- | ------ | ----- | ------ | ---------------------------------------- | ----------------------------------------------- |
| 创建账号 | REG-01 | 注册成功  | 邮箱未被注册 | 填写 Name、Email、密码（≥6 位），点击 Create account | 创建账号并自动登录，跳转 `/onboarding`                      |
| 创建账号 | REG-02 | 姓名为空  | —      | Name 留空提交                                | 提示 "Please enter your name."                    |
| 创建账号 | REG-03 | 邮箱为空  | —      | Email 留空提交                               | 提示 "Please enter your email."                   |
| 创建账号 | REG-04 | 密码过短  | —      | 密码少于 6 位提交                               | 提示 "Password must be at least 6 characters."    |
| 创建账号 | REG-05 | 邮箱重复  | 该邮箱已注册 | 使用已注册邮箱提交                                | 提示 "An account with this email already exists." |
| 登录入口 | REG-06 | 跳转登录页 | 处于注册页  | 点击页脚登录链接                                 | 跳转 `/login`                                     |


---

## 3. 引导页（Profile 提取） `/onboarding`


| 功能        | 用例编号  | 用例名称          | 前置条件                    | 操作步骤                                                        | 预期结果                                                           |
| --------- | ----- | ------------- | ----------------------- | ----------------------------------------------------------- | -------------------------------------------------------------- |
| 入口选择      | OB-01 | 选择上传 CV 方式    | 已登录，处于 Welcome 步骤       | 点击 "Upload my CV"                                           | 进入 CV 上传步骤                                                     |
| 入口选择      | OB-02 | 选择对话方式        | 已登录，处于 Welcome 步骤       | 点击 "Chat with the assistant"                                | 进入对话式信息采集步骤                                                    |
| 跳过引导      | OB-03 | Welcome 页跳过   | 处于 Welcome 步骤           | 点击 "Skip and explore"                                       | 保存空 profile（name = "Friend"），跳转 Dashboard，触发欢迎通知               |
| 跳过引导      | OB-04 | 中途跳过          | 处于非 Welcome 步骤          | 点击页头 "Skip for now"                                         | 同 OB-03                                                        |
| 上传 CV     | OB-05 | 选择合法文件        | 处于上传步骤                  | 选择 .pdf/.doc/.docx/.txt 文件                                  | 显示文件名和移除按钮，"Extract info" 变为可用                                 |
| 上传 CV     | OB-06 | 未选文件时按钮禁用     | 处于上传步骤，未选文件             | 观察 "Extract info" 按钮                                        | 按钮禁用，无法点击                                                      |
| 上传 CV     | OB-07 | 移除已选文件        | 已选择文件                   | 点击文件旁移除按钮                                                   | 文件名清空，"Extract info" 恢复禁用                                      |
| 上传 CV     | OB-08 | 返回上一步         | 处于上传步骤                  | 点击 Back                                                     | 返回 Welcome 步骤，已选文件被清空                                          |
| AI 提取     | OB-09 | 模拟提取流程        | 已选择文件                   | 点击 "Extract info"                                           | 显示 3 阶段进度动画，约 2.5s 后完成，进入 Review 步骤（demo 固定结果：projects 含 1 条占位项目 "Project extracted from CV"，其余为空） |
| 对话采集      | OB-10 | 完成 6 轮问答      | 处于对话步骤                  | 依次回答 name / school / major / degree / skills / coursework，其中 school、major、degree 写入 education[0] | 最后一题回答后约 600ms 自动进入 Review 步骤                                  |
| 对话采集      | OB-11 | 空消息不可发送       | 处于对话步骤                  | 输入框为空时尝试发送                                                  | 无法发送                                                           |
| 对话采集      | OB-12 | 逗号解析列表        | 回答 skills/coursework 问题 | 输入 "Python, SQL, React"                                     | 按逗号解析为多个技能/课程条目                                                |
| Review 确认 | OB-13 | 编辑并保存 profile | 处于 Review 步骤            | 编辑 Name / Education（Degree、School、Major、GPA、Start、End）/ Skills / Coursework / 最近实习（Role、Company、Start、End、Description），Name 非空，点击 "Continue to dashboard" | 保存 profile（GPA 解析为数字，非法值存为 null；教育/实习 End 留空存为 null；实习全空则不保存），触发欢迎通知，跳转 Dashboard      |
| Review 确认 | OB-14 | Name 为空不可保存   | 处于 Review 步骤            | 清空 Name 字段                                                  | "Continue to dashboard" 禁用                                     |
| Review 确认 | OB-15 | 返回上一步         | 处于 Review 步骤            | 点击 Back                                                     | 有上传文件时回上传步骤，否则回对话步骤                                            |


---

## 4. Dashboard `/`


| 功能            | 用例编号  | 用例名称          | 前置条件           | 操作步骤                     | 预期结果                                               |
| ------------- | ----- | ------------- | -------------- | ------------------------ | -------------------------------------------------- |
| 欢迎区           | DB-01 | 显示用户名         | 已完成 profile    | 打开 Dashboard             | 欢迎语显示 profile.name；name 为空时显示 "Friend"             |
| 申请追踪卡片        | DB-02 | 查看申请汇总并跳转     | 存在若干申请记录       | 查看卡片并点击                  | 卡片显示总数/进行中/offer 数，点击跳转 `/applications`            |
| Today's focus | DB-03 | 显示今日焦点        | 存在未完成周焦点或低信心技能 | 查看 Today's focus 区域      | 最多展示 3 条，点击可跳转对应目标的 plan-tracking                  |
| 职业目标列表        | DB-04 | 查看目标进度        | 已添加至少一个目标      | 查看目标列表                   | 每项显示进度条和状态，点击进入该目标的 plan-tracking                  |
| 职业目标列表        | DB-05 | 无目标空状态        | 未添加任何目标        | 打开 Dashboard             | 显示空状态及 CTA，点击跳转 `/new-goal`                        |
| 职业目标列表        | DB-06 | 新增目标入口        | —              | 点击列表底部 "New Career Goal" | 跳转 `/new-goal`                                     |
| Profile 侧栏    | DB-07 | 查看 profile 摘要 | 已完成 profile    | 查看侧栏                     | 头部显示 degree · major 与 school（取 education[0]，含起止时间）；下方展示 skills / projects（标题+时间段）/ coursework / internships     |
| Profile 侧栏    | DB-08 | 编辑入口          | —              | 点击侧栏 Edit 按钮             | 跳转 `/onboarding`（注意：非 `/profile`）                  |
| 校友推荐          | DB-09 | 查看推荐校友        | 已有职业目标         | 查看推荐区                    | 最多 3 人，点击进入 `/alumni/:id`；显示 pending/completed 会议数 |
| 校友推荐          | DB-10 | 浏览全部校友        | —              | 点击 "Browse network"      | 跳转 `/alumni`                                       |


---

## 5. 新增职业目标 `/new-goal`


| 功能   | 用例编号  | 用例名称      | 前置条件                   | 操作步骤                  | 预期结果                                  |
| ---- | ----- | --------- | ---------------------- | --------------------- | ------------------------------------- |
| 选择目标 | NG-01 | 查看推荐排序    | profile 含 skills，education[0] 含 major | 打开页面                  | 目标卡片按匹配度排序，首项标 "Recommended"          |
| 选择目标 | NG-02 | 已添加目标不可重复 | 某目标已添加                 | 查看该目标卡片               | 显示 "Added" 徽章，按钮禁用为 "Already added"   |
| 选择目标 | NG-03 | 取消返回      | —                      | 点击 Cancel             | 返回 Dashboard，不创建目标                    |
| 信心测评 | NG-04 | 开始测评      | 选中某目标                  | 点击 "Start quiz"       | 进入技能信心测评，各项初始信心为 3                    |
| 信心测评 | NG-05 | 逐项评分      | 处于测评步骤                 | 为每项技能选 1–5 分          | 显示 answered/total 进度                  |
| 信心测评 | NG-06 | 未答完不可提交   | 仍有未评分项                 | 观察 "Build my plan" 按钮 | 按钮禁用，全部答完后才可用                         |
| 信心测评 | NG-07 | 完成创建目标    | 全部评分完成                 | 点击 "Build my plan"    | 创建目标，触发职位/校友匹配通知，跳转该目标的 plan-tracking |
| 信心测评 | NG-08 | 更换目标      | 处于测评步骤                 | 点击 "Change goal"      | 返回目标选择步骤                              |


---

## 6. 学习计划 `/career-goal/:goalId/plan-tracking`


| 功能   | 用例编号  | 用例名称            | 前置条件            | 操作步骤                      | 预期结果                                                    |
| ---- | ----- | --------------- | --------------- | ------------------------- | ------------------------------------------------------- |
| 页面守卫 | PT-01 | 目标不存在           | URL 中 goalId 无效 | 直接访问该 URL                 | 显示提示及 "Back to dashboard" / "Add a goal"                |
| 周焦点  | PT-02 | 勾选完成周焦点         | 存在周焦点任务         | 勾选/取消勾选任务                 | 任务完成状态切换，进度同步更新                                         |
| 周焦点  | PT-03 | 更换焦点            | 存在周焦点任务         | 点击 "Pick different focus" | 重新抽取一组周焦点                                               |
| 周焦点  | PT-04 | 全部完成状态          | 所有步骤均完成         | 查看周焦点卡片                   | 显示 "All caught up!"                                     |
| 进度统计 | PT-05 | 查看统计卡片          | 目标已有评分数据        | 查看页面顶部                    | 显示 Overall / Needs focus(信心1-2) / Already strong(信心4-5) |
| 技能模块 | PT-06 | 展开模块手风琴         | 目标含技能模块         | 打开页面                      | 模块按信心+进度排序，第一项默认展开                                      |
| 技能模块 | PT-07 | 勾选 Action Steps | 模块已展开           | 勾选/取消步骤                   | 步骤状态切换，模块进度条与总进度更新                                      |
| 技能模块 | PT-08 | 标记资源已读          | 模块含资源           | 勾选资源 / 点击外链               | 已读状态切换；外链在新窗口打开                                         |
| 重新评分 | PT-09 | 触发重新评分          | 某模块已完成 ≥2 步     | 查看模块                      | 出现重新评分提示，可选 1–5 分或 "Not now"                            |
| 关联推荐 | PT-10 | 跳转校友/职位         | 模块含关联链接         | 点击对应链接                    | 分别跳转 `/alumni?expertise=...` 和 `/jobs?goal=...`         |


---

## 7. 职位搜索 `/jobs`


| 功能    | 用例编号   | 用例名称          | 前置条件             | 操作步骤                                                             | 预期结果                                          |
| ----- | ------ | ------------- | ---------------- | ---------------------------------------------------------------- | --------------------------------------------- |
| 页面守卫  | JOB-01 | 无目标空状态        | 未添加任何职业目标        | 访问 `/jobs`                                                       | 显示空状态及 CTA，跳转 `/new-goal`                     |
| 目标筛选  | JOB-02 | 切换目标          | 已有多个目标           | 使用下拉切换目标                                                         | 列表刷新，URL 同步 `?goal={goalId}`                  |
| 目标筛选  | JOB-03 | 无效 goal 参数    | URL 含无效 `?goal=` | 直接访问                                                             | 自动回退到第一个目标                                    |
| 统计卡片  | JOB-04 | 查看汇总          | 已有保存/申请记录        | 查看顶部卡片                                                           | 显示 Saved / Applied / Open roles / Referral 数量 |
| 保存职位  | JOB-05 | 收藏职位          | 列表中有职位           | 点击书签按钮                                                           | 加入 Saved jobs 区，持久化到 localStorage             |
| 保存职位  | JOB-06 | 取消收藏          | 已收藏某职位           | 在 Saved 区点击 Unsave                                               | 从收藏中移除                                        |
| 职位详情  | JOB-07 | 查看详情弹窗        | 列表中有职位           | 点击职位卡片                                                           | 弹窗展示描述、技能、match%、面试流程等                        |
| 申请职位  | JOB-08 | 普通职位申请        | 未申请该职位           | 点击 "Apply Now"，在 CV 弹窗点击 "Save to application tracker"           | 创建 standard 申请，按钮变绿                           |
| 申请职位  | JOB-09 | Partner 职位申请  | 未申请该 partner 职位  | 点击 "Apply with referral"，勾选确认项后点击 "Submit referral with this CV" | 创建 partner 申请；未勾选确认项时提交按钮禁用                   |
| 申请职位  | JOB-10 | 撤销申请          | 已申请某职位           | 再次点击已申请（绿色）按钮                                                    | 撤销申请（partner 和 standard 均支持）                  |
| 定制 CV | JOB-11 | 自动生成 CV       | 打开申请弹窗           | 观察 CV 文本区                                                        | 根据 profile + 职位自动生成，可内联编辑                     |
| 定制 CV | JOB-12 | 导出 CV         | 打开申请弹窗           | 分别点击 PDF / Word / PNG 导出                                         | PDF 走打印流程，Word/PNG 下载文件                       |
| 定制 CV | JOB-13 | 公司申请外链        | 普通（非 partner）职位  | 查看弹窗                                                             | 显示公司 careers 页外链卡片                            |
| 定制 CV | JOB-14 | 取消申请流程        | 打开申请弹窗           | 点击 Cancel                                                        | 关闭弹窗，不创建申请                                    |
| 路线图   | JOB-15 | 折叠/展开 Roadmap | —                | 点击 JobRoadmap 折叠控件                                               | 静态时间线展开/收起                                    |


---

## 8. 申请追踪 `/applications`

> 面试教练功能已迁移至独立模块 [§9 AI Coaching](#9-ai-coaching-ai-coaching)。本页仅负责申请状态追踪，并提供跳转入口。

| 功能   | 用例编号   | 用例名称         | 前置条件           | 操作步骤                            | 预期结果                                                                   |
| ---- | ------ | ------------ | -------------- | ------------------------------- | ---------------------------------------------------------------------- |
| 汇总卡片 | APP-01 | 查看汇总         | 已有申请记录         | 查看顶部卡片                          | 显示 Total / Partner / Self-tracked / In progress / Offers               |
| 页头说明 | APP-02 | 辅导入口文案      | —              | 查看页头描述                          | 文案含指向 `/ai-coaching` 的 **AI Coaching** 链接（面试复盘 + 语音模拟）              |
| 空状态  | APP-03 | 无申请记录        | 无任何申请          | 访问页面                            | 显示空状态，引导前往 `/jobs`                                                     |
| 目标筛选 | APP-04 | 按目标筛选        | 有多个目标的申请       | 选择某目标或 All goals                | 列表按所选目标过滤，URL 同步 `?goal=`                                              |
| 状态管理 | APP-05 | Partner 自动推进 | 存在 partner 申请  | 等待/点击 Refresh                   | 状态按提交时间自动推进（8h→24h→48h→120h 各阶段）                                       |
| 状态管理 | APP-06 | 手动更新状态       | 存在 standard 申请 | 使用状态下拉选择                        | 可选 Applied / Screening / Interview / Offer / Rejected / Withdrawn，立即保存 |
| 辅导入口 | APP-07 | 快捷跳转        | 该申请已有复盘或模拟存档   | 点击卡片底部 "Open in AI Coaching"     | 跳转 `/ai-coaching`；侧栏 AI Coaching 高亮；显示 review/mock 数量摘要              |


---

## 9. AI Coaching `/ai-coaching`

> 独立面试辅导工作区。按已申请岗位（`applicationId`）组织；**面试复盘**与**模拟面试**均支持多场次存档（`aichh:interview-reviews-v2`、`aichh:mock-interviews-v1`）。

| 功能     | 用例编号  | 用例名称       | 前置条件              | 操作步骤                                                                 | 预期结果                                                                 |
| ------ | ----- | ---------- | ----------------- | -------------------------------------------------------------------- | -------------------------------------------------------------------- |
| 页面守卫   | AC-01 | 无申请空状态     | 无任何申请             | 访问页面                                                                 | 显示空状态，引导前往 `/jobs` 申请岗位                                              |
| 汇总区    | AC-02 | 查看统计卡片     | 已有申请              | 查看页头汇总区                                                            | 显示 Applications / Reviews archived / Mocks archived 数量及 Demo mode 提示 |
| 申请列表   | AC-03 | 按申请展开      | 已有申请              | 点击某申请卡片                                                             | 展开该岗位；默认 Interview review Tab；卡片显示 review/mock 数量徽章（若有）            |
| 申请列表   | AC-04 | 切换辅导 Tab   | 已展开某申请            | 点击 Interview review / Mock interview                                   | 两个 Tab 按申请独立记忆；切换后展示对应面板                                            |
| 面试复盘   | AC-05 | 上传合法音频     | Review Tab        | 上传 MP3/WAV/M4A/WebM 且 ≤25MB 的文件                                      | 模拟分析（transcribe → summarize → score → recommend）；**追加**一条存档         |
| 面试复盘   | AC-06 | 文件类型错误     | Review Tab        | 上传非音频文件                                                            | 提示 "Please upload an audio file..."                                |
| 面试复盘   | AC-07 | 文件过大       | Review Tab        | 上传 >25MB 音频                                                       | 提示 "File is too large..."                                          |
| 面试复盘   | AC-08 | 分析失败       | Review Tab        | 模拟分析异常                                                            | 提示 "Analysis failed. Please try another file."                     |
| 面试复盘   | AC-09 | 查看复盘存档     | 已有复盘记录            | 展开 Archived reviews 某条                                              | 显示总分、5 维度分、摘要、改进建议、可折叠 transcript；刷新后仍在                          |
| 面试复盘   | AC-10 | 删除单条复盘     | 已有复盘记录            | 点击 Delete                                                            | 仅删除该条；其他复盘存档保留                                                       |
| 模拟面试   | AC-11 | 开始模拟面试     | Mock Tab          | 点击 "Start mock interview"                                            | Coach TTS 播报首题；显示 Q 1/4 进度与对话区                                         |
| 模拟面试   | AC-12 | 语音作答       | 模拟进行中             | Record answer → 说话 → Submit answer；重复至 4 题                         | 对话区记录 coach/user 轮次；提交后 Coach 播报下一题或进入评估                               |
| 模拟面试   | AC-13 | 提前结束       | 已至少回答 1 题         | 点击 End early                                                         | 基于已有回答异步评估并存档                                                         |
| 模拟面试   | AC-14 | 查看模拟结果     | 模拟完成              | 查看完成区与 Archived mock interviews                                    | 显示维度评分、建议、transcript；**追加**一条存档                                      |
| 模拟面试   | AC-15 | 再开一场       | 刚完成一场模拟           | 点击 "Start another mock"                                              | 重置为 idle，可开始新一场（新存档）                                                  |
| 模拟面试   | AC-16 | 删除单条模拟     | 已有模拟存档            | 在 Archived mock interviews 中点击 Delete                                | 仅删除该条存档                                                              |
| 模拟面试   | AC-17 | 不支持语音环境    | 浏览器无 STT/TTS     | 点击开始模拟                                                             | 提示使用 Chrome/Edge；显示功能受限说明                                            |


---

## 10. Profile 编辑 `/profile`


| 功能    | 用例编号  | 用例名称         | 前置条件          | 操作步骤                                                  | 预期结果                                   |
| ----- | ----- | ------------ | ------------- | ----------------------------------------------------- | -------------------------------------- |
| 基础信息  | PF-01 | 编辑并保存        | 已登录且有 profile | 修改 Name，点击 "Save changes" | 保存到 localStorage（updatedAt 同步刷新），绿色 "Saved" 提示显示约 2.5s |
| 基础信息  | PF-02 | Name 为空保存    | —             | 清空 Name 后保存                                           | 保存成功，name 被存为 "Friend"                 |
| 技能/课程 | PF-03 | 逗号分隔编辑       | —             | 在 Skills/Coursework 输入 "A, B, C" 后保存                  | 解析为列表保存，Dashboard 侧栏同步显示               |
| 教育经历  | PF-04 | 新增/编辑教育经历    | —             | 点击 Education 区 Add，填写 Degree / School / Major / GPA / Start / End 后保存 | 新增教育经历生效；GPA 解析为数字，非法值存为 null；End 留空存为 null（表示在读）      |
| 实习经历  | PF-05 | 新增/编辑实习      | —             | 点击 Internships 区 Add，填写 Role / Company / Start / End / Description 后保存 | 新增实习生效；End 留空保存为 null（表示至今）            |
| 项目经历  | PF-06 | 新增/编辑项目      | —             | 点击 Projects 区 Add，填写 Title / Start / End / Description 后保存 | 新增项目生效；End 留空保存为 null（表示至今）            |
| 条目管理  | PF-07 | 删除条目         | 已有教育/实习/项目条目  | 点击条目旁 Remove                                          | 该条目被移除                                 |
| 条目管理  | PF-08 | 空白条目过滤       | —             | 添加条目但关键字段留空后保存                                        | 全空条目被自动过滤，不保存                          |
| 导航    | PF-09 | 返回 Dashboard | —             | 点击 Back                                               | 跳转 Dashboard                           |


---

## 11. 设置 `/settings`


| 功能   | 用例编号   | 用例名称       | 前置条件 | 操作步骤                     | 预期结果                                                      |
| ---- | ------ | ---------- | ---- | ------------------------ | --------------------------------------------------------- |
| 账号信息 | SET-01 | 查看当前邮箱     | 已登录  | 打开设置页                    | 当前邮箱只读展示                                                  |
| 登出   | SET-02 | 退出登录       | 已登录  | 点击 Log out               | 清除 session，跳转 `/login`                                    |
| 修改密码 | SET-03 | 修改成功       | 已登录  | 输入正确当前密码 + 新密码（≥6 位），提交  | 修改成功，输入框清空，"Updated" 提示显示约 2.5s                           |
| 修改密码 | SET-04 | 新密码过短      | 已登录  | 新密码少于 6 位提交              | 提示 "New password must be at least 6 characters."          |
| 修改密码 | SET-05 | 当前密码错误     | 已登录  | 输入错误的当前密码提交              | 提示 "Current password is incorrect."                       |
| 通知开关 | SET-06 | 切换应用内通知    | 已登录  | 切换通知开关                   | 状态写入 `aichh:settings-notifications`（on/off），刷新后保持         |
| 重置数据 | SET-07 | 重置 demo 数据 | 已登录  | 点击 "Reset demo data" 并确认 | 清除 profile/goals/tracking、`interview-reviews-v2`、`mock-interviews-v1` 等数据但保留账号，跳转 `/onboarding` 并刷新页面 |
| 删除账号 | SET-08 | 删除账号       | 已登录  | 点击 "Delete account" 并确认  | 删除账号及全部 demo 数据，跳转 `/login`                               |


---

## 12. 校友网络 `/alumni`


| 功能   | 用例编号  | 用例名称     | 前置条件                                | 操作步骤                            | 预期结果                                |
| ---- | ----- | -------- | ----------------------------------- | ------------------------------- | ----------------------------------- |
| 搜索   | AL-01 | 关键词搜索    | 处于 Browse 标签                        | 输入 role/company/topic 关键词       | 列表实时过滤，关键词同步到 URL `?q=`             |
| 搜索   | AL-02 | 无结果空状态   | —                                   | 输入无匹配的关键词                       | 显示空状态提示                             |
| 行业筛选 | AL-03 | 按行业过滤    | 处于 Browse 标签                        | 点击行业 pill / "All industries"    | 列表按行业过滤                             |
| 匹配徽章 | AL-04 | 显示 Match | 已有职业目标且某校友匹配                        | 查看校友卡片                          | 显示 Match 徽章                         |
| 卡片操作 | AL-05 | 查看资料/外链  | —                                   | 点击 "View profile" / LinkedIn 图标 | 分别跳转 `/alumni/:id` / 新窗口打开 LinkedIn |
| 请求状态 | AL-06 | 已发送请求标记  | 已向某校友发送请求                           | 查看该校友卡片                         | 显示 "Request sent"                   |
| 我的请求 | AL-07 | 查看请求统计   | 切换到 My requests 标签（`?tab=requests`） | 查看顶部                            | 显示 Total / Pending / Completed      |
| 我的请求 | AL-08 | 标记会议完成   | 存在 pending 请求                       | 点击 "Mark completed"             | 请求变为 Completed，触发成功通知               |
| 我的请求 | AL-09 | 撤回请求     | 存在 pending 请求                       | 点击 Withdraw                     | 请求被移除                               |


---

## 13. 校友详情 `/alumni/:id`


| 功能   | 用例编号  | 用例名称      | 前置条件          | 操作步骤                           | 预期结果                                        |
| ---- | ----- | --------- | ------------- | ------------------------------ | ------------------------------------------- |
| 页面守卫 | AD-01 | 无效校友 ID   | URL 中 id 无效   | 直接访问                           | 显示 "Profile not found" + "Back to network"  |
| 资料展示 | AD-02 | 查看校友资料    | 有效校友 ID       | 打开页面                           | 展示匿名名、角色、公司、专业、话题、专长、可用性；LinkedIn 新窗口打开     |
| 会议请求 | AD-03 | 提交咖啡聊天请求  | 未有 pending 请求 | 选择 Topic，输入 ≥20 字符消息，点击提交      | 创建 pending 请求并发通知，跳转 `/alumni?tab=requests` |
| 会议请求 | AD-04 | 消息过短      | —             | 输入少于 20 字符的消息                  | 提交按钮禁用，实时显示剩余字数                             |
| 会议请求 | AD-05 | 添加/删除偏好时间 | —             | 在偏好时间输入后回车/点击 Add；点击 tag 上的删除  | 时间 tag 添加/移除（该项可选）                          |
| 会议请求 | AD-06 | 重复请求替换    | 已有 pending 请求 | 再次提交新请求                        | 新请求替换旧 pending 请求                           |
| 会议请求 | AD-07 | 撤回已有请求    | 已有 pending 请求 | 在 "Request sent" 卡片点击 Withdraw | 请求被撤回，可重新发起                                 |


---

## 14. 全局导航与守卫（RootLayout）


| 功能         | 用例编号   | 用例名称         | 前置条件          | 操作步骤                                         | 预期结果                                                   |
| ---------- | ------ | ------------ | ------------- | -------------------------------------------- | ------------------------------------------------------ |
| 登录守卫       | NAV-01 | 未登录拦截        | 未登录           | 直接访问任意受保护路由                                  | 重定向 `/login`                                           |
| Profile 守卫 | NAV-02 | 无 profile 拦截 | 已登录但无 profile | 访问 `/` 等受保护路由                                | 重定向 `/onboarding`                                      |
| 主导航        | NAV-03 | 侧栏导航跳转       | 已登录           | 点击 Dashboard / Applications / AI Coaching / Jobs / Network | 跳转对应页面，当前项高亮                                           |
| 目标侧栏       | NAV-04 | 目标列表与新增      | 已登录           | 查看侧栏，点击 `+`                                  | 列出所有目标；`+` 跳转 `/new-goal`；无目标时显示 "Add your first goal" |
| 目标排序       | NAV-05 | 上移/下移目标      | 有 ≥2 个目标      | 在目标 `⋯` 菜单点击 Move up / Move down             | 顺序调整；首项 Move up、末项 Move down 禁用                        |
| 删除目标       | NAV-06 | 删除目标         | 有目标           | 在 `⋯` 菜单点击 "Delete goal" 并确认                 | 目标被删除；若当前正浏览该目标，跳回 Dashboard                           |
| 用户菜单       | NAV-07 | 菜单跳转         | 已登录           | 分别点击 Profile / Settings / Log out            | 分别跳转 `/profile`、`/settings`、清除 session 后跳转 `/login`    |


---

## 15. 通知系统（全局组件）


| 功能   | 用例编号  | 用例名称    | 前置条件                  | 操作步骤                       | 预期结果                   |
| ---- | ----- | ------- | --------------------- | -------------------------- | ---------------------- |
| 未读角标 | NT-01 | 显示未读数   | 存在未读通知                | 查看顶栏铃铛                     | 显示未读数角标，最多显示 "9+"      |
| 通知操作 | NT-02 | 点击通知跳转  | 通知带链接                 | 点击该通知                      | 标记已读并导航到对应页面           |
| 通知操作 | NT-03 | 全部已读    | 存在多条未读                | 点击 "Mark all read"         | 全部通知标记为已读              |
| 通知操作 | NT-04 | 删除/清空   | 存在通知                  | 点击单条 Dismiss / "Clear all" | 单条删除 / 列表清空            |
| 自动触发 | NT-05 | 进度里程碑通知 | 某目标进度达到 25/50/75/100% | 完成步骤使进度跨越里程碑               | 自动触发对应通知，去重 key 防止重复推送 |


