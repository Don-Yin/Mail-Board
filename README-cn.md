# Mail-Board
[English Version](README.md)
这是一个邮件统计查看器和内容分析器。

## 主导航
首先是这个导航页面：
![主导航界面](public/index.png)

## 分析
点击分析进入邮件查看页面：
- 显示收件箱每份邮件的内容
- 调用antropic分析：
> 这封邮件的重要程度（需要填写下 configuration.yaml 文件）
> 如果忽略/删除邮件会面临的后果
> 下一步该咋办，怎么回，怎么操作
然后直接显示在右边

| 自动回复分析                      | 推荐操作                          |
|-------------------------------|-------------------------------|
| ![邮件分析 1](public/email-1.png) | ![邮件分析 2](public/email-2.png) |

## 统计看板
点击统计进入这个页面：
![统计界面](public/stats.png)
- 发送/接收邮件趋势
- 每日平均值和总计
- 文件夹分布可视化
- 邮件类别分布
- 未读邮件跟踪

## 系统要求
- 只支持 MacOS
- 下载 Outlook 客户端
- 将 Outlook 版本设置为传统版（legacy）
![传统设置](public/legacy.png)
- 登录所有账户（可以是任何账户，例如 Google）。支持多个账户
- 在 configuration.yaml 中设置背景信息（删除文件名中的 .example）

## 安装设置
1. ```git clone```
2. 将 `configuration.example.yaml` 改为 `configuration.yaml`
3. 配置 Outlook 传统版
4. 运行 ```python main.py```
5. 在弹出窗口中允许访问的 Outlook 客户端

## 下一步
- 马上就整一个 requirement.txt

## 许可证
本项目根据包含的 LICENSE 文件授权。
禁止商业使用。

## 为什么要做这个
- 合并多个服务时获取邮件统计数据非常麻烦
- 大学邮箱不允许开放 API 控制台，麻烦
- 这个完全在本地运行，不需要 API，使用 AppleScript 直接从系统文件读取邮件

---
注意：此界面需要传统版 Outlook 兼容性才能实现完整功能。