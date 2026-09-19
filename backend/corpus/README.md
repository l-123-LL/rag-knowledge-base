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
# 逐篇导入（管理员 Key 见 backend/.env）
$files = Get-ChildItem backend/corpus -Filter "*.md" | Where-Object { $_.Name -ne "README.md" }
foreach ($f in $files) {
  $body = @{ text = (Get-Content $f.FullName -Raw -Encoding UTF8); source = $f.BaseName; doc_key = $f.BaseName; version = 1 } | ConvertTo-Json
  Invoke-RestMethod -Uri "http://127.0.0.1:8000/ingest" -Method Post -Body $body -ContentType "application/json" -Headers @{ "X-API-Key" = $env:ADMIN_API_KEY }
}
```

## 注意

这批资料是**公开资料的替代方案**，不是某家企业的真实内部资料。真实企业上线时应当替换成自己的产品手册、FAQ 与售后政策，并重新校准 `RAG_MIN_SCORE`（当前 0.42 是在示例语料上标定的）。
