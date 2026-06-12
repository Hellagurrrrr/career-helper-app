# API 设计文档（AI Career Helper）

---

## 目录

1. [总体约定](#1-总体约定)
2. [认证 Auth](#2-认证-auth)
3. [用户画像 Profile](#3-用户画像-profile)
4. [职业目标 Goals](#4-职业目标-goals)
5. [学习计划追踪 Tracking](#5-学习计划追踪-tracking)
6. [职位 Jobs 与收藏 Saved Jobs](#6-职位-jobs-与收藏-saved-jobs)
7. [定制 CV Tailored CV](#7-定制-cv-tailored-cv)
8. [申请记录 Applications](#8-申请记录-applications)
9. [AI Coaching（面试复盘 + 模拟面试）](#9-ai-coaching面试复盘--模拟面试)
10. [校友网络 Alumni 与会议 Meetings](#10-校友网络-alumni-与会议-meetings)
11. [通知 Notifications](#11-通知-notifications)
12. [错误码汇总](#12-错误码汇总)
13. [localStorage 键与 API 的迁移映射](#13-localstorage-键与-api-的迁移映射)

---

## 1. 总体约定

### 1.1 基础信息


| 项目       | 约定                                                  |
| -------- | --------------------------------------------------- |
| Base URL | `https://career.helper.com/v1`                      |
| 协议       | HTTPS only                                          |
| 数据格式     | 请求/响应均为 `application/json; charset=utf-8`（文件上传除外）   |
| 认证方式     | `Authorization: Bearer <access_token>`（JWT）         |
| 时间格式     | Unix 毫秒时间戳（与前端现有 `submittedAt`、`createdAt` 等字段保持一致） |
| ID 格式    | 服务端生成的字符串 ID（UUID 或短 ID）                            |
| 版本策略     | URL 路径版本号 `/v1`；破坏性变更升级大版本                          |


### 1.2 通用响应结构

成功响应直接返回资源对象或数组；失败响应统一为：

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Password must be at least 6 characters.",
    "details": { "field": "password" }
  }
}
```

### 1.3 通用状态码


| 状态码 | 含义             |
| --- | -------------- |
| 200 | 成功             |
| 201 | 创建成功           |
| 204 | 成功且无返回体（删除等）   |
| 400 | 参数校验失败         |
| 401 | 未登录 / token 失效 |
| 403 | 无权限访问该资源       |
| 404 | 资源不存在          |
| 409 | 冲突（如邮箱已注册）     |
| 413 | 上传文件过大         |
| 422 | 业务规则不满足        |
| 429 | 触发限流           |
| 500 | 服务端错误          |


### 1.4 分页约定

列表接口支持游标分页：

```
GET /v1/notifications?limit=20&cursor=eyJpZCI6...
```

```json
{
  "items": [],
  "nextCursor": "eyJpZCI6...",
  "total": 132
}
```

### 1.5 资源归属

除「公共目录类」资源（职业目标目录、职位目录、校友目录）外，其余资源均归属当前登录用户；服务端从 token 解析 `userId`，客户端不传。

---

## 2. 认证 Auth

### 2.1 数据模型

```ts
type AuthUser = {
  id: string;
  email: string;
  name: string;
  createdAt: number;
};

type AuthTokens = {
  accessToken: string;   // 有效期短，如 30 分钟
  refreshToken: string;  // 有效期长，如 30 天
};
```

### 2.2 接口列表


| 方法   | 路径               | 说明                   | 认证            |
| ---- | ---------------- | -------------------- | ------------- |
| POST | `/auth/register` | 注册并自动登录              | 否             |
| POST | `/auth/login`    | 邮箱密码登录               | 否             |
| POST | `/auth/refresh`  | 刷新 access token      | refresh token |
| POST | `/auth/logout`   | 注销（吊销 refresh token） | 是             |
| GET  | `/auth/me`       | 获取当前登录用户             | 是             |


### 2.3 POST /auth/register

请求：

```json
{ "name": "Alex Chen", "email": "alex@example.com", "password": "secret123" }
```

校验规则（与前端用例 REG-01~05 一致）：

- `name` 非空；
- `email` 非空、格式合法，服务端 trim + 转小写后判重；
- `password` 至少 6 位；
- 邮箱已存在返回 `409 EMAIL_TAKEN`。

响应 `201`：

```json
{
  "user": { "id": "u_01", "email": "alex@example.com", "name": "Alex Chen", "createdAt": 1780000000000 },
  "tokens": { "accessToken": "...", "refreshToken": "..." }
}
```

### 2.4 POST /auth/login

请求：

```json
{ "email": "alex@example.com", "password": "secret123" }
```

- 邮箱 trim + 转小写后匹配（用例 LOGIN-05）；
- 邮箱不存在返回 `404 ACCOUNT_NOT_FOUND`；
- 密码错误返回 `401 WRONG_PASSWORD`。

响应 `200`：同注册。

登录后客户端根据 `GET /profile` 是否为 `404` 决定跳转 Dashboard 还是 `/onboarding`（用例 LOGIN-01/02）。

---

## 3. 用户画像 Profile

每个用户至多一份 profile。

### 3.1 数据模型

```ts
type Education = {
  degree: string;          // 学位，如 "BSc" / "MSc"
  school: string;
  major: string;
  grade: number | null;    // GPA，如 3.7；未填为 null
  start: string;           // "YYYY-MM"，学位开始时间
  end: string | null;      // "YYYY-MM"；null 表示在读 / 预计毕业
};

type Internship = {
  title: string;
  company: string;
  start: string;           // "YYYY-MM"，如 "2025-06"
  end: string | null;      // null 表示至今
  description: string;
};

type Project = {
  title: string;
  start: string;           // "YYYY-MM"
  end: string | null;      // null 表示至今
  description: string;
};

type Profile = {
  name: string;
  education: Education[];     // 教育经历，可多段（本科、硕士等）
  internships: Internship[];  // 实习经历
  projects: Project[];        // 项目经历
  skills: string[];           // 技能，驱动目标推荐 / 职位匹配 / 定制 CV
  coursework: string[];       // 相关课程
  updatedAt: number;
};
```

> 说明：
>
> - `education` / `internships` / `projects` 均为结构化数组。
> - 展示层的「学校 / 专业」取 `education[0]`（约定数组按时间倒序，最新的在前）。

### 3.2 接口列表


| 方法     | 路径                              | 说明                                       |
| ------ | ------------------------------- | ---------------------------------------- |
| GET    | `/profile`                      | 获取当前用户 profile，未创建返回 404                 |
| PUT    | `/profile`                      | 创建或整体覆盖 profile（onboarding 完成时调用）        |
| POST   | `/profile/extract-cv`           | 上传 CV 文件，AI 提取 profile 草稿（异步）            |
| GET    | `/profile/onboarding-chat`      | 获取当前对话式采集会话；无会话返回 404                    |
| POST   | `/profile/onboarding-chat`      | 开始或**恢复**对话式采集会话（OB-10/OB-12）            |
| POST   | `/profile/onboarding-chat/answers` | 回答当前问题，返回下一问题或 `complete` + draft（OB-10）|
| DELETE | `/profile/onboarding-chat`      | 放弃当前会话（重新开始 / 退出对话采集）                   |

> 关于 `PUT /profile`（对应 Review 步骤 OB-13）：
>
> - 服务端做轻量归一化：教育/实习/项目的 `end` 为空串时存为 `null`（表示在读/至今）；**完全空白的实习条目自动丢弃**（实习全空则不保存）。
> - `grade`（GPA）由前端在 Review 表单解析为数字，非法值传 `null`；服务端按 `number | null` 存储。
> - 当 profile 由「无」首次创建（onboarding 完成，含跳过引导 OB-03/04 与对话/CV 采集）时，服务端触发一条**欢迎通知**（见 §11）；后续在 Profile 编辑页保存（PF-01）不再触发。


### 3.3 POST /profile/extract-cv

对应 onboarding 的「Upload my CV → Extract info」流程（用例 OB-05~09），落地时接入真实解析服务。

请求：`multipart/form-data`，字段 `file`（`.pdf/.doc/.docx/.txt`，≤ 10 MB）。

响应 `202`：

```json
{ "taskId": "task_01", "status": "processing" }
```

轮询 `GET /profile/extract-cv/{taskId}`：

```json
{
  "taskId": "task_01",
  "status": "complete",        // processing | complete | failed
  "stage": "structuring",      // parsing | extracting | structuring（用于前端 3 阶段进度动画）
  "draft": {
    "name": "...",
    "skills": ["Python"],
    "education": [{ "degree": "BSc", "school": "State University", "major": "Computer Science", "grade": 3.7, "start": "2022-09", "end": "2026-06" }],
    "projects": [{ "title": "Course planner app", "start": "2025-09", "end": "2025-12", "description": "..." }]
  }
}
```

`draft` 为 `Profile` 的部分字段，前端进入 Review 步骤让用户确认后再 `PUT /profile`。

### 3.4 对话式信息采集 Onboarding Chat

对应 onboarding 的「Chat with the assistant」流程（用例 OB-10~12）。由助手（AI）逐轮提问采集信息，**直到收集到足够信息后自动结束**并产出 `draft` 供 Review 步骤确认；会话**按用户持久化且可恢复**——中途退出后再次进入会从中断处继续（OB-12）。落地时由 LLM 驱动提问与抽取，demo 用固定问题脚本模拟。

#### 数据模型

```ts
type OnboardingChatTurn = {
  id: string;
  role: "assistant" | "user";
  text: string;
  timestamp: number;
};

type OnboardingChatSession = {
  id: string;
  status: "in_progress" | "complete";
  question: string | null;        // 当前待回答的问题；complete 时为 null
  questionIndex: number;          // 已提问数量
  totalQuestions: number;         // 预计问题总数（demo 固定脚本）
  turns: OnboardingChatTurn[];    // 完整对话记录
  draft: Partial<Profile> | null; // complete 时产出，供 Review 步骤使用
};
```

> 每个用户至多一个进行中的会话。`POST /profile/onboarding-chat` 若已有 `in_progress` 会话则直接返回它（恢复，OB-12），否则新建并返回首个问题。

#### POST /profile/onboarding-chat（开始 / 恢复）

无请求体。响应 `200`（含首个或当前待答问题）：

```json
{
  "id": "obc_01",
  "status": "in_progress",
  "question": "Hi! I'm your career assistant. What's your name?",
  "questionIndex": 0,
  "totalQuestions": 6,
  "turns": [
    { "id": "t_01", "role": "assistant", "text": "Hi! ... What's your name?", "timestamp": 1780000000000 }
  ],
  "draft": null
}
```

#### POST /profile/onboarding-chat/answers（回答）

请求：

```json
{ "text": "Python, SQL, React" }
```

约束与行为：

- 空消息返回 `400 VALIDATION_ERROR`（OB-11 前端禁用，服务端兜底）；
- 无进行中的会话返回 `404`；会话已 `complete` 返回 `422`；
- 技能 / 课程类回答按逗号解析为列表；学校 / 专业 / 学位写入 `education[0]`；
- 助手判断信息已足够（demo：问完脚本）后，会话置为 `complete` 并返回 `draft`。

`complete` 响应示例：

```json
{
  "id": "obc_01",
  "status": "complete",
  "question": null,
  "questionIndex": 6,
  "totalQuestions": 6,
  "turns": [ /* ... */ ],
  "draft": {
    "name": "Alex Chen",
    "education": [{ "degree": "BSc", "school": "State University", "major": "Computer Science", "grade": null, "start": "", "end": null }],
    "skills": ["Python", "SQL", "React"],
    "coursework": ["Data Structures"],
    "internships": [],
    "projects": []
  }
}
```

前端拿到 `draft` 后进入 Review 步骤，确认/编辑后 `PUT /profile`（OB-13）。

#### DELETE /profile/onboarding-chat

放弃当前会话，响应 `204`。用于「重新开始对话采集」或离开该方式。

---

## 4. 职业目标 Goals

分为公共目录（`CatalogGoal`）和用户目标（`UserGoal`）两类资源。

### 4.1 数据模型

```ts
type SkillResource = { title: string; type: string; url: string };

type CoreSkill = {
  id: string;
  name: string;
  description: string;
  defaultStatus: string;
  whatToDo: string[];           // 步骤清单
  resources: SkillResource[];
  jobSkillKeywords: string[];   // 用于匹配职位/校友
};

// 公共目录，「能选什么职业方向」的模板。
// 用户可以选择多个职业方向。
type CatalogGoal = {
  id: string;
  title: string;
  description: string;
  color: string;
  matchSignals: string[];
  defaultStatus: "active" | "exploring";
  coreSkills: CoreSkill[];
};

// 用户选择的职业方向，「我选了哪个方向、进展如何」的实例。
type UserGoal = {
  id: string;
  catalogId: string;
  title: string;
  description: string;
  color: string;
  status: "active" | "exploring";
  progress: number;                    // 0–100，服务端根据 confidence + tracking 计算
  lastUpdated: string;
  createdAt: number;
  confidence: Record<string, number>;  // skillId -> 1–5 自评
  sortOrder: number;                   // Dashboard 改变排序
};
```

### 4.2 接口列表


| 方法     | 路径                          | 说明                        |
| ------ | --------------------------- | ------------------------- |
| GET    | `/goal-catalog`             | 获取职业目标目录（公共，可缓存）          |
| GET    | `/goal-catalog/{catalogId}` | 目录单项详情（含 coreSkills）      |
| GET    | `/goals`                    | 当前用户的目标列表（按 sortOrder 排序） |
| POST   | `/goals`                    | 从目录添加一个目标                 |
| GET    | `/goals/{goalId}`           | 单个目标详情                    |
| PATCH  | `/goals/{goalId}`           | 更新状态 / confidence 等       |
| DELETE | `/goals/{goalId}`           | 删除目标                      |
| PUT    | `/goals/order`              | 整体提交拖拽后的排序                |


### 4.3 关键请求示例

POST `/goals`：

```json
{ "catalogId": "1" }
```

同一 `catalogId` 重复添加返回 `409 GOAL_ALREADY_ADDED`。

PATCH `/goals/{goalId}`（信心自评，用例参见 Plan Tracking 页）：

```json
{ "confidence": { "skill-react": 4 } }
```

PUT `/goals/order`：

```json
{ "goalIds": ["g_02", "g_01", "g_03"] }
```

---

## 5. 学习计划追踪 Tracking

按「目标 → 技能模块」两级组织。

### 5.1 数据模型

```ts
type ModuleTracking = {
  completedSteps: number[];        // whatToDo 中已勾选步骤的下标
  consumedResources: number[];     // 已消费资源的下标
  stepsCompletedSinceRerate: number;
  rerateDismissed: boolean;
};

type GoalTracking = {
  modules: Record<string, ModuleTracking>;  // skillId -> ModuleTracking
  weekStartedAt: number;
  weekFocus: string[];             // "skillId:stepIndex" 形式的周焦点
};
```

### 5.2 接口列表


| 方法   | 路径                                                                     | 说明                                                 |
| ---- | ---------------------------------------------------------------------- | -------------------------------------------------- |
| GET  | `/goals/{goalId}/tracking`                                             | 获取该目标的全部追踪状态                                       |
| PUT  | `/goals/{goalId}/tracking/modules/{skillId}/steps/{stepIndex}`         | 勾选某步骤（body: `{ "completed": true }`）               |
| PUT  | `/goals/{goalId}/tracking/modules/{skillId}/resources/{resourceIndex}` | 标记资源已消费                                            |
| POST | `/goals/{goalId}/tracking/modules/{skillId}/rerate-dismiss`            | 关闭「重新自评」提示                                         |
| PUT  | `/goals/{goalId}/tracking/week-focus`                                  | 设置本周焦点（body: `{ "weekFocus": ["skill-react:0"] }`） |


> 进度计算：模块进度 = 已完成步骤数 / 总步骤数；目标 `progress` 由服务端按 confidence 与各模块进度加权计算，写入 `UserGoal.progress`，避免前后端口径不一致。

---

## 6. 职位 Jobs 与收藏 Saved Jobs

职位目录为公共资源，按目标目录组织。

### 6.1 数据模型

```ts
type JobListing = {
  id: string;
  catalogGoalId: string;
  title: string;
  company: string;
  companyTagline?: string;
  location: string;
  type: string;               // Full-time / Internship ...
  salary: string;
  posted: string;
  skills: string[];
  partner: boolean;           // 平台合作职位
  exclusive: boolean;         // 独家内推职位
  applicationUrl?: string;    // 非独家职位的企业官网申请链接
  description?: string;       // 富文本 JD；缺省时由模板生成
};
```

### 6.2 接口列表


| 方法     | 路径                                           | 说明                                                                       |
| ------ | -------------------------------------------- | ------------------------------------------------------------------------ |
| GET    | `/jobs?catalogGoalId=1&partner=true&q=react` | 职位列表（按职业目标过滤，支持关键词、partner/exclusive 过滤、分页）                              |
| GET    | `/jobs/{jobId}`                              | 职位详情（含 description、面试流程）。响应中附带 `matchScore`（基于当前用户 profile 计算的匹配度 0–100） |
| GET    | `/saved-jobs?goalId=g_01`                    | 当前用户在某目标下收藏的职位                                                           |
| PUT    | `/saved-jobs/{jobId}`                        | 收藏（body: `{ "goalId": "g_01" }`）                                         |
| DELETE | `/saved-jobs/{jobId}?goalId=g_01`            | 取消收藏                                                                     |


---

## 7. 定制 CV Tailored CV

CV 文本生成改由服务端 LLM 完成，导出（PDF/Word/PNG）仍由前端处理。


| 方法   | 路径                      | 说明                           |
| ---- | ----------------------- | ---------------------------- |
| POST | `/tailored-cv/generate` | 基于 profile + 职位上下文生成定制 CV 文本 |


请求：

```json
{ "jobId": "j_101", "goalId": "g_01" }
```

响应 `200`：

```json
{
  "cvText": "ALEX CHEN\nFull-Stack Developer ...",
  "highlights": ["Matched 6/8 required skills", "Emphasized React project"]
}
```

用户可在前端编辑后用于导出或随内推提交（见 8.3）。

---

## 8. 申请记录 Applications

岗位申请分两类：`partner`（内推，状态由系统流水线推进）与 `standard`（自投，状态手动维护）。

### 8.1 数据模型

```ts
type ManualApplicationStatus =
  | "applied" | "screening" | "interview"
  | "offer" | "rejected" | "withdrawn";

type PartnerPipelineCode =
  | "referral_sent" | "under_review" | "interview"
  | "final_round" | "offer_extended";

type JobApplication = {
  id: string;
  kind: "partner" | "standard";
  goalId: string;
  jobId: string;
  title: string;
  company: string;
  submittedAt: number;
  // kind = partner：由服务端流水线推进，只读
  partnerStatus?: PartnerPipelineCode;
  // kind = standard：用户手动维护
  manualStatus?: ManualApplicationStatus;
};
```

### 8.2 接口列表


| 方法     | 路径                          | 说明                                                |
| ------ | --------------------------- | ------------------------------------------------- |
| GET    | `/applications?goalId=g_01` | 申请列表（可按职业目标过滤），附带汇总统计                             |
| POST   | `/applications`             | 创建申请记录                                            |
| PATCH  | `/applications/{id}`        | 更新 `manualStatus`（仅 standard 类型；partner 类型返回 422） |
| DELETE | `/applications/{id}`        | 删除/撤回记录                                           |


GET `/applications` 响应示例：

```json
{
  "items": [
    {
      "id": "app_01",
      "kind": "standard",
      "goalId": "g_01",
      "jobId": "j_101",
      "title": "Software Engineer Intern",
      "company": "Stripe",
      "submittedAt": 1780000000000,
      "manualStatus": "interview",
      "reviewCount": 2,
      "mockCount": 1
    }
  ],
  "summary": { "total": 8, "partner": 3, "selfTracked": 5, "inProgress": 6, "offers": 1 }
}
```

### 8.3 POST /applications

自投（用户在企业官网申请后回来记录）：

```json
{ "kind": "standard", "goalId": "g_01", "jobId": "j_101" }
```

内推（携带定制 CV 一键提交）：

```json
{ "kind": "partner", "goalId": "g_01", "jobId": "j_205", "cvText": "ALEX CHEN ..." }
```

约束：

- `jobId` 必须存在且独家职位才允许 `kind=partner`，否则 `422 NOT_EXCLUSIVE_JOB`；
- 同一职位重复申请返回 `409 ALREADY_APPLIED`；
- partner 申请创建后 `partnerStatus=referral_sent`，后续由服务端推进并通过通知（见 §11）告知用户。

---

## 9. AI Coaching（面试复盘 + 模拟面试）

包含面试复盘和模拟面试两个子功能。

### 9.1 页面级接口


| 方法  | 路径                          | 说明                                        |
| --- | --------------------------- | ----------------------------------------- |
| GET | `/ai-coaching/summary`      | 汇总：申请数、复盘存档总数、模拟存档总数                      |
| GET | `/ai-coaching/applications` | 可辅导的申请列表（含每岗位的 `reviewCount`、`mockCount`） |


`GET /ai-coaching/summary` 响应示例：

```json
{
  "applicationCount": 5,
  "reviewCount": 8,
  "mockCount": 3
}
```

### 9.2 共用类型

```ts
type InterviewDimensionScore = {
  id: string;        // role_fit | depth | communication | problem_solving | presence
  label: string;
  score: number;     // demo 为 1–10 分制（如 7.2）
  narrative: string;
};

type CoachingContext = {
  applicationId: string;
  jobTitle: string;
  company: string;
  goalTitle?: string;
  skills: string[];
};
```

分析/出题上下文由服务端从 `JobApplication` + 关联 `JobListing` + `UserGoal` 拼装，客户端无需传入。

### 9.3 面试复盘 Interview Reviews

同一申请可保留多份复盘。

```ts
type InterviewAnalysisStep =
  | "transcribing" | "summarizing" | "scoring" | "recommendations" | "complete";

type InterviewReview = {
  id: string;
  applicationId: string;
  fileName: string;
  uploadedAt: number;
  durationSec: number | null;
  transcript: string;
  overallSummary: string;
  dimensions: InterviewDimensionScore[];
  improvementAdvice: string;
};
```

> 说明：`InterviewAnalysisStep` 仅用于上传分析过程中的前端进度动画；完成后持久化的 `InterviewReview` 不含 `status` 字段。

### 9.4 复盘接口列表


| 方法     | 路径                                                | 说明                            |
| ------ | ------------------------------------------------- | ----------------------------- |
| GET    | `/applications/{id}/interview-reviews`            | 该申请的全部复盘存档（按 `uploadedAt` 倒序） |
| POST   | `/applications/{id}/interview-reviews`            | 上传录音并发起分析（异步），**新增一条**记录      |
| GET    | `/applications/{id}/interview-reviews/{reviewId}` | 单条复盘详情/分析状态                   |
| DELETE | `/applications/{id}/interview-reviews/{reviewId}` | 删除单条复盘                        |


### 9.5 POST /applications/{id}/interview-reviews

请求：`multipart/form-data`，字段 `file`。

约束：

- 格式限 MP3 / WAV / M4A / WebM，否则 `400 UNSUPPORTED_AUDIO_FORMAT`；
- 大小 ≤ 25 MB，否则 `413 FILE_TOO_LARGE`；
- 每次上传均创建新记录，不覆盖历史复盘。

响应 `202`：

```json
{ "id": "ir_01", "applicationId": "app_01", "status": "transcribing" }
```

分析上下文（职位、公司、目标、技能关键词，即 `InterviewReviewContext`）由服务端从申请记录关联获取，无需客户端传入。

### 9.6 模拟面试 Mock Interviews

针对已申请岗位进行语音模拟面试（默认 **4 轮**问答，`MOCK_QUESTION_COUNT`），结束后生成与复盘相同结构的维度评分与建议。

```ts
type MockInterviewTurn = {
  id: string;
  role: "coach" | "user";
  text: string;
  timestamp: number;
};

type MockInterviewSession = {
  id: string;
  applicationId: string;
  jobTitle: string;
  company: string;
  goalTitle?: string;
  skills: string[];
  startedAt: number;
  completedAt: number;
  durationSec: number;
  turns: MockInterviewTurn[];
  transcript: string;
  overallSummary: string;
  dimensions: InterviewDimensionScore[];
  improvementAdvice: string;
};
```

### 9.6.1 模拟面试接口列表


| 方法     | 路径                                                     | 说明                            |
| ------ | ------------------------------------------------------ | ----------------------------- |
| GET    | `/applications/{id}/mock-interviews`                   | 该申请的全部模拟面试存档                  |
| POST   | `/applications/{id}/mock-interviews`                   | 创建会话（返回 `sessionId` + 首题）     |
| POST   | `/applications/{id}/mock-interviews/{sessionId}/turns` | 提交用户语音转写/回答，返回下一题或 `complete` |
| GET    | `/applications/{id}/mock-interviews/{sessionId}`       | 会话详情（进行中轮询 / 结束后含评分）          |
| DELETE | `/applications/{id}/mock-interviews/{sessionId}`       | 删除单条存档                        |


### 9.7 Demo 交互流程（与实现对齐）

**面试复盘**

1. 用户在 AI Coaching 页展开某申请 →「Interview review」Tab；
2. 上传 MP3/WAV/M4A/WebM（≤ 25 MB）；
3. 前端依次展示 `transcribing → summarizing → scoring → recommendations → complete`；
4. 生成 `InterviewReview` ；
5. 「Archived reviews」列表展示该岗位全部历史复盘，支持单条删除。

**模拟面试**

1. 展开申请 →「Mock interview」Tab → 点击「Start mock interview」；
2. Coach 通过 `speechSynthesis`（TTS）播报题目；
3. 用户点击「Record answer」→ 说话 →「Submit answer」（`webkitSpeechRecognition`）；
4. 重复至 4 题或点击「End early」（至少 1 轮用户回答后可提前结束）；
5. `runMockInterviewEvaluation` 异步评估；
6. 「Archived mock interviews」列表展示历史模拟，支持单条删除。

落地时：Coach 语音 → 服务端 TTS；用户输入 → 流式 STT；评估 → LLM 结构化输出。

---

## 10. 校友网络 Alumni 与会议 Meetings

校友目录为公共资源，会议请求归属用户。

### 10.1 数据模型

```ts
type AlumniProfile = {
  id: string;
  firstName: string;
  lastInitial: string;
  role: string;
  company: string;
  industry: string;
  graduationYear: number;
  major: string;
  university: string;
  yearsExperience: number;
  bio: string;
  expertise: string[];
  topics: string[];
  responseTime: string;
  availability: string;
  goalAlignment: string[];   // 对齐的 catalogGoalId
  avatarGradient: string;
  linkedinUrl: string;
};

type MeetingRequest = {
  id: string;
  alumniId: string;
  topic: string;
  message: string;
  preferredTimes: string[];
  submittedAt: number;
  status: "pending" | "completed" | "withdrawn";
  completedAt?: number;
};
```

### 10.2 接口列表


| 方法    | 路径                            | 说明                      |
| ----- | ----------------------------- | ----------------------- |
| GET   | `/alumni?goalId=g_01&q=react` | 校友列表（按用户目标/技能推荐排序，支持搜索） |
| GET   | `/alumni/{alumniId}`          | 校友详情                    |
| GET   | `/meetings?alumniId=a1`       | 当前用户的会议请求列表             |
| POST  | `/meetings`                   | 发起会议请求                  |
| PATCH | `/meetings/{id}`              | 更新状态（标记完成 / 撤回）         |


POST `/meetings` 请求：

```json
{
  "alumniId": "a1",
  "topic": "Career path in full-stack",
  "message": "Hi Sarah, ...",
  "preferredTimes": ["2026-06-15T10:00+08:00", "2026-06-16T14:00+08:00"]
}
```

对同一校友已有 `pending` 会议时重复发起返回 `409 MEETING_ALREADY_PENDING`。

---

## 11. 通知 Notifications

落地后由服务端事件（partner 流水线推进、会议状态变化、周焦点提醒等）生成。

### 11.1 数据模型

```ts
type AppNotification = {
  id: string;
  type: "system" | "job" | "alumni" | "meeting" | "milestone" | "week";
  severity: "info" | "success" | "warning";
  title: string;
  body: string;
  link?: string;        // 应用内路由，如 "/applications"
  createdAt: number;
  read: boolean;
  dedupKey?: string;    // 服务端按 (userId, dedupKey) 去重
};
```

### 11.2 接口列表


| 方法     | 路径                                    | 说明                                              |
| ------ | ------------------------------------- | ----------------------------------------------- |
| GET    | `/notifications?unread=true&limit=20` | 通知列表（每用户最多保留最近 50 条）                            |
| POST   | `/notifications/read`                 | 批量标记已读（body: `{ "ids": ["n1"] }`，`ids` 缺省则全部已读） |
| DELETE | `/notifications/{id}`                 | 删除单条                                            |


> 可选演进：提供 `GET /notifications/stream`（SSE）或 WebSocket 推送，替代轮询。

---

## 12. 错误码汇总


| code                       | HTTP | 说明                            |
| -------------------------- | ---- | ----------------------------- |
| `VALIDATION_ERROR`         | 400  | 通用参数校验失败，`details.field` 指明字段 |
| `UNSUPPORTED_AUDIO_FORMAT` | 400  | 面试复盘录音格式不支持（§9.5）             |
| `SPEECH_NOT_SUPPORTED`     | 422  | 浏览器不支持语音合成/识别（模拟面试，demo 前端校验） |
| `MOCK_SESSION_INCOMPLETE`  | 422  | 模拟面试无有效用户回答即结束                |
| `UNAUTHORIZED`             | 401  | 未携带或无效 token                  |
| `WRONG_PASSWORD`           | 401  | 密码错误                          |
| `FORBIDDEN`                | 403  | 访问他人资源                        |
| `ACCOUNT_NOT_FOUND`        | 404  | 邮箱未注册                         |
| `NOT_FOUND`                | 404  | 资源不存在                         |
| `EMAIL_TAKEN`              | 409  | 邮箱已注册                         |
| `GOAL_ALREADY_ADDED`       | 409  | 目标重复添加                        |
| `ALREADY_APPLIED`          | 409  | 职位重复申请                        |
| `MEETING_ALREADY_PENDING`  | 409  | 已有待处理会议请求                     |
| `FILE_TOO_LARGE`           | 413  | 上传文件超限                        |
| `NOT_EXCLUSIVE_JOB`        | 422  | 非独家职位不允许内推                    |
| `RATE_LIMITED`             | 429  | 请求过于频繁                        |
| `INTERNAL_ERROR`           | 500  | 服务端错误                         |


---

## 13. localStorage 键与 API 的迁移映射


| localStorage 键                                          | 对应 API 资源                                 | 备注                       |
| ------------------------------------------------------- | ----------------------------------------- | ------------------------ |
| `aichh:accounts` / `aichh:session`                      | §2 Auth                                   | 改为服务端密码哈希 + JWT          |
| `aichh:profile`                                         | §3 `/profile`                             | —                        |
| `aichh:goals`                                           | §4 `/goals`                               | 排序改为 `sortOrder` 字段      |
| `aichh:tracking`                                        | §5 `/goals/{goalId}/tracking`             | 进度计算移至服务端                |
| `aichh:job-applications-v1`                             | §8 `/applications`                        | `jobIndex` 迁移为稳定 `jobId` |
| `aichh:interview-reviews-v1`                            | §9（已废弃）                                   | 单条/申请；启动时自动迁移至 v2        |
| `aichh:interview-reviews-v2`                            | §9 `/applications/{id}/interview-reviews` | 多场次复盘存档                  |
| `aichh:mock-interviews-v1`                              | §9 `/applications/{id}/mock-interviews`   | 语音模拟面试 + 评估存档            |
| `aichh:saved-jobs-by-goal`                              | §6 `/saved-jobs`                          | `jobIndex` 迁移为 `jobId`   |
| `aichh:notifications`                                   | §11 `/notifications`                      | 改为服务端事件驱动生成              |
| `aichh:meetings`                                        | §10 `/meetings`                           | —                        |
| 前端常量 `GOAL_CATALOG` / `JOBS_BY_GOAL` / `ALUMNI_CATALOG` | §4/§6/§10 公共目录接口                          | 由后端数据库维护，可缓存             |


