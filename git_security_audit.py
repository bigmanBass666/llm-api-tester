#!/usr/bin/env python3
"""
Git 历史密钥安全审计工具
扫描所有提交中的敏感信息泄露
"""

import subprocess
import re
import sys
from datetime import datetime

# 定义敏感信息正则表达式模式
SENSITIVE_PATTERNS = {
    'API Keys': [
        # 通用 API 密钥模式
        (r'(?:api|key|secret|token|auth)[-_]?(?:key|secret|token)?[\s:=]+["\']?[\w-]{20,}["\']?', 'Generic API Key'),
        # NVIDIA API Key
        (r'nvapi-[A-Za-z0-9_-]{40,}', 'NVIDIA API Key'),
        # OpenAI API Key
        (r'sk-[A-Za-z0-9]{48,}', 'OpenAI API Key'),
        # AWS Access Key
        (r'AKIA[A-Z0-9]{16}', 'AWS Access Key'),
        # AWS Secret Key
        (r'(?i)aws[_-]?secret[_-]?access[_-]?key[\s:=]+["\']?[A-Za-z0-9/+=]{40}["\']?', 'AWS Secret Key'),
        # Google API Key
        (r'AIza[A-Za-z0-9_-]{35}', 'Google API Key'),
        # GitHub Token
        (r'ghp_[A-Za-z0-9]{36,}', 'GitHub Personal Token'),
        (r'github_pat_[A-Za-z0-9_]{22,}', 'GitHub PAT'),
        (r'gho_[A-Za-z0-9]{36,}', 'GitHub OAuth Token'),
        (r'ghu_[A-Za-z0-9]{36,}', 'GitHub User Token'),
        (r'ghs_[A-Za-z0-9]{36,}', 'GitHub Server Token'),
        (r'ghr_[A-Za-z0-9]{36,}', 'GitHub Refresh Token'),
        # Slack Token
        (r'xox[baprs]-[A-Za-z0-9-]+', 'Slack Token'),
        # Stripe Key
        (r'(?:sk|pk)_(?:live|test)_[A-Za-z0-9]+', 'Stripe Key'),
        # 智谱 AI
        (r'[a-f0-9]{32}\.[A-Za-z0-9]+', 'Zhipu AI API Key Pattern'),
    ],
    'Passwords & Credentials': [
        # 密码模式
        (r'(?i)password[\s:=]+["\'][^"\']+["\']', 'Password Assignment'),
        (r'(?i)passwd[\s:=]+["\'][^"\']+["\']', 'Passwd Assignment'),
        (r'(?i)pwd[\s:=]+["\'][^"\']+["\']', 'Pwd Assignment'),
        # 数据库连接字符串
        (r'(?:mysql|postgresql|mongodb|redis)://[^:\s]+:[^@\s]+@', 'Database Connection String'),
        # JWT Token
        (r'eyJ[A-Za-z0-9_-]*\.eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*', 'JWT Token'),
    ],
    'Private Keys & Certificates': [
        # 私钥
        (r'-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----', 'Private Key Header'),
        (r'-----BEGIN ENCRYPTED PRIVATE KEY-----', 'Encrypted Private Key'),
        # 证书
        (r'-----BEGIN CERTIFICATE-----', 'Certificate'),
        # SSH 密钥
        (r'ssh-(?:rsa|ed25519|ecdsa) [A-Za-z0-9+/=]+', 'SSH Public Key'),
    ],
    'Environment Variables with Secrets': [
        # 环境变量中的敏感信息
        (r'(?:NVIDIA_API_KEY|ZHIPU_API_KEY|OPENAI_API_KEY|API_KEY|SECRET_KEY|AUTH_TOKEN|ACCESS_TOKEN)[\s:=]+["\']?[^\s"\']{10,}["\']?', 'Env Var with Secret'),
    ],
}

def run_git_command(cmd):
    """执行 git 命令并返回输出"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        return result.stdout
    except Exception as e:
        print(f"Error running command: {e}")
        return ""

def scan_commit(commit_hash):
    """扫描单个提交"""
    findings = []
    
    # 获取提交的 diff
    diff_cmd = f"git show {commit_hash} --format='' --no-color"
    diff_output = run_git_command(diff_cmd)
    
    if not diff_output:
        return findings
    
    lines = diff_output.split('\n')
    current_file = None
    
    for line_num, line in enumerate(lines, 1):
        # 跟踪当前文件
        if line.startswith('+++ b/') or line.startswith('--- a/'):
            current_file = line.split('/', 1)[-1] if '/' in line else line
        
        # 只检查添加的行（以 + 开头，但不是 +++）
        if not line.startswith('+') or line.startswith('+++'):
            continue
        
        content = line[1:]  # 移除 + 号
        
        # 检查每个模式类别
        for category, patterns in SENSITIVE_PATTERNS.items():
            for pattern, pattern_name in patterns:
                try:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        finding = {
                            'commit': commit_hash,
                            'file': current_file,
                            'line': line_num,
                            'category': category,
                            'pattern_type': pattern_name,
                            'match': mask_sensitive_data(match.group()),
                            'context': get_context(line),
                        }
                        findings.append(finding)
                except re.error:
                    continue
    
    return findings

def mask_sensitive_data(match):
    """遮蔽敏感数据（只显示前后几位）"""
    if len(match) <= 12:
        return match[:4] + '*' * 4 + match[-4:] if len(match) > 8 else '*' * len(match)
    return match[:6] + '*' * 8 + match[-6:]

def get_context(line, context_length=80):
    """获取上下文信息"""
    if len(line) > context_length:
        return line[:context_length] + '...'
    return line

def main():
    print("="*80)
    print("🔒 Git 历史安全审计工具")
    print(f"⏰ 扫描时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    print()
    
    # 获取所有提交哈希
    print("📋 正在获取提交列表...")
    commits = run_git_command("git rev-list --all").strip().split('\n')
    total_commits = len(commits)
    print(f"   发现 {total_commits} 个提交需要扫描")
    print()
    
    # 扫描所有提交
    all_findings = []
    print("🔍 开始扫描提交历史...")
    print("-" * 80)
    
    for i, commit in enumerate(commits, 1):
        if not commit.strip():
            continue
            
        commit = commit.strip()
        
        # 显示进度
        sys.stdout.write(f"\r   进度: [{i}/{total_commits}] 扫描: {commit[:8]}... ")
        sys.stdout.flush()
        
        findings = scan_commit(commit)
        all_findings.extend(findings)
    
    print(f"\n\n✅ 扫描完成！")
    print("-" * 80)
    print()
    
    # 生成报告
    generate_report(all_findings)

def generate_report(findings):
    """生成详细的安全审计报告"""
    
    print("="*80)
    print("📊 安全审计报告")
    print("="*80)
    print()
    
    # 统计信息
    print(f"📈 总体统计:")
    print(f"   ⚠️  发现潜在泄露: {len(findings)} 处")
    
    if not findings:
        print("\n✅ 太好了！未发现明显的敏感信息泄露。")
        print("💡 建议：定期运行此扫描以确保持续安全。")
        return
    
    # 按类别分组
    by_category = {}
    for finding in findings:
        cat = finding['category']
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(finding)
    
    print(f"\n📂 按类别分布:")
    for category, items in by_category.items():
        print(f"   • {category}: {len(items)} 处")
    
    # 按严重程度排序显示发现
    print(f"\n" + "="*80)
    print("🚨 详细发现列表（按风险等级排序）")
    print("="*80)
    print()
    
    # 高危：私钥、证书
    high_risk = [f for f in findings if f['category'] in ['Private Keys & Certificates']]
    # 中危：密码、数据库连接串
    medium_risk = [f for f in findings if f['category'] in ['Passwords & Credentials']]
    # 低危：API 密钥（可能误报）
    low_risk = [f for f in findings if f['category'] in ['API Keys', 'Environment Variables with Secrets']]
    
    risk_sections = [
        ("🔴 高危 - 私钥/证书泄露", high_risk),
        ("🟠 中危 - 密码/凭证泄露", medium_risk),
        ("🟡 低危 - API 密钥（需人工确认）", low_risk),
    ]
    
    for title, risk_findings in risk_sections:
        if risk_findings:
            print(f"\n{'─'*80}")
            print(f"{title} ({len(risk_findings)} 处)")
            print(f"{'─'*80}")
            
            # 按提交分组显示
            by_commit = {}
            for finding in risk_findings:
                commit = finding['commit']
                if commit not in by_commit:
                    by_commit[commit] = []
                by_commit[commit].append(finding)
            
            for commit, commit_findings in list(by_commit.items())[:10]:  # 最多显示10个提交
                print(f"\n📝 提交: {commit[:12]}...")
                
                for i, finding in enumerate(commit_findings[:5], 1):  # 每个提交最多5条
                    print(f"\n   [{i}] 文件: {finding['file']}")
                    print(f"       类型: {finding['pattern_type']}")
                    print(f"       匹配: {finding['match']}")
                    print(f"       内容: {finding['context']}")
                
                if len(commit_findings) > 5:
                    print(f"\n      ... 还有 {len(commit_findings)-5} 条发现")
    
    # 提供修复建议
    print(f"\n\n{'='*80}")
    print("💡 修复建议")
    print("="*80)
    print("""
1. 🔴 紧急处理（高危）：
   • 立即轮换所有泄露的私钥和证书
   • 使用 BFG Repo Cleaner 或 git filter-repo 清除历史
   • 强制推送清理后的仓库（需通知团队成员）

2. 🟠 重要处理（中危）：
   • 修改所有泄露的密码
   • 更新数据库连接字符串等凭证
   • 将配置移至环境变量或密钥管理服务

3. 🟡 建议处理（低危）：
   • 审查 API 密钥是否为真实密钥或测试数据
   • 如为真实密钥，立即在相应平台重新生成
   • 配置 pre-commit hooks 防止未来泄露

4. 🛡️ 预防措施：
   • 确保 .gitignore 包含所有敏感文件
   • 安装 detect-secrets 或类似工具
   • 定期运行安全审计扫描
   • 使用环境变量或密钥管理服务存储敏感信息
""")
    
    # 输出摘要到文件
    output_file = "security_audit_report.txt"
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"安全审计报告 - {datetime.now()}\n")
            f.write(f"总发现数: {len(findings)}\n\n")
            for finding in findings:
                f.write(f"提交: {finding['commit']}\n")
                f.write(f"文件: {finding['file']}\n")
                f.write(f"类型: {finding['pattern_type']}\n")
                f.write(f"内容: {finding['context']}\n\n")
        print(f"\n📄 详细报告已保存至: {output_file}")
    except Exception as e:
        print(f"\n⚠️ 无法保存报告文件: {e}")

if __name__ == "__main__":
    main()
