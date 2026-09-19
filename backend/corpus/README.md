# 演示语料说明

这里放的是**公开、许可清晰**的资料，用来把知识库从示例文本换成接近真实的文档。每篇文件头部都标注了来源与许可。

| 文件 | 内容 | 来源 | 许可 |
| --- | --- | --- | --- |
| `01-mall平台说明.md` | 电商平台功能说明（商品、订单、购物车、售后模块） | [macrozheng/mall](https://github.com/macrozheng/mall) | Apache-2.0 |
| `02-mall-swarm说明.md` | 微服务版电商平台说明 | [macrozheng/mall-swarm](https://github.com/macrozheng/mall-swarm) | Apache-2.0 |
| `03-mall-tiny说明.md` | 精简版电商系统说明 | [macrozheng/mall-tiny](https://github.com/macrozheng/mall-tiny) | Apache-2.0 |
| `04-litemall说明.md` | 商城系统说明 | [linlinjava/litemall](https://github.com/linlinjava/litemall) | MIT |
| `05-快递暂行条例.md` | 国务院令第 697 号全文（快递投递、验收、赔偿等） | [中国政府网](https://www.gov.cn/zhengce/content/2018-03/27/content_5277801.htm) | 官方公开文本（法律文本不受著作权限制） |

## 为什么这样选

- **优先选许可明确、可合法再分发的资料**：Apache-2.0 / MIT 允许商用与再分发；法律、法规文本依著作权法不适用著作权保护。
- **刻意避开**：没有声明许可的仓库（默认保留所有权利）、GPL 等 copyleft 许可（会传染到整个作品集）、需要登录或付费的资料。
- **主题贴合客服场景**：电商平台说明里有商品、订单、支付、物流、售后流程；快递条例里有投递、验收、赔偿时效——正好覆盖客服高频问题。

## 怎么导入

```powershell
# 在仓库根目录执行（脚本自己从 backend/.env 读 ADMIN_API_KEY）
powershell -ExecutionPolicy Bypass -File scripts/ingest-corpus.ps1
```

脚本是**幂等**的：分块 id 由「来源 + 序号 + 内容摘要」生成，重复执行只会跳过已存在的分块，输出本次真正新增的数量。当前导入结果是 **74 个分块**。

## 注意

这批资料是**公开资料的替代方案**，不是某家企业的真实内部资料。真实企业上线时应当替换成自己的产品手册、FAQ 与售后政策。

导入后必须重新标定拒答阈值：`RAG_MIN_SCORE` 当前是 **0.37**（域内最低 0.377 / 域外最高 0.360，域内 10/10 保留、域外 8/8 挡下），标定命令：

```powershell
cd backend
..\.venv\Scripts\python.exe -m evaluation.calibrate_threshold
```

问题集在 `backend/evaluation/corpus_questions.json`（10 条域内 + 8 条域外），换语料后请一起更新。
