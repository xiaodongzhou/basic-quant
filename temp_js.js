        // ========== Tab 切换功能 ==========
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const tabId = btn.dataset.tab;
                
                // 更新按钮状态
                document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                
                // 更新内容区域
                document.querySelectorAll('.tab-content').forEach(content => {
                    content.classList.remove('active');
                });
                document.getElementById(tabId === 'live' ? 'live-trading' : 
                                      tabId === 'backtest' ? 'backtest' : 'management').classList.add('active');
                
                // 如果切换到用户管理，加载数据
                if (tabId === 'management') {
                    loadManagementData();
                }
            });
        });
        
        // ========== 策略配置功能 ==========
        const strategySelect = document.getElementById('strategy-select');
        const symbolSelect = document.getElementById('symbol-select');
        const addTaskBtn = document.getElementById('add-task-btn');
        
        // 检查表单完成状态
        function checkFormComplete() {
            if (strategySelect.value && symbolSelect.value) {
                addTaskBtn.disabled = false;
            } else {
                addTaskBtn.disabled = true;
            }
        }
        
        strategySelect.addEventListener('change', () => {
            updateStrategyParams();
            checkFormComplete();
        });
        symbolSelect.addEventListener('change', checkFormComplete);
        
        // 更新策略参数配置界面
        function updateStrategyParams() {
            const strategy = strategySelect.value;
            const paramsDiv = document.getElementById('strategy-params');
            
            if (!strategy) {
                paramsDiv.innerHTML = '';
                return;
            }
            
            let paramsHtml = '<h4>📋 策略参数</h4>';
            
            switch (strategy) {
                case 'ma_cross':
                    paramsHtml += `
                        <div class="form-group">
                            <label>快线周期:</label>
                            <input type="number" id="fast_ma" value="5" min="1" max="50">
                        </div>
                        <div class="form-group">
                            <label>慢线周期:</label>
                            <input type="number" id="slow_ma" value="20" min="1" max="200">
                        </div>
                    `;
                    break;
                case 'bollinger':
                    paramsHtml += `
                        <div class="form-group">
                            <label>布林带周期:</label>
                            <input type="number" id="bb_period" value="20" min="5" max="100">
                        </div>
                        <div class="form-group">
                            <label>标准差倍数:</label>
                            <input type="number" id="bb_std" value="2" min="1" max="5" step="0.1">
                        </div>
                    `;
                    break;
                case 'rsi':
                    paramsHtml += `
                        <div class="form-group">
                            <label>RSI周期:</label>
                            <input type="number" id="rsi_period" value="14" min="5" max="50">
                        </div>
                        <div class="form-group">
                            <label>超买阈值:</label>
                            <input type="number" id="rsi_overbought" value="70" min="50" max="90">
                        </div>
                        <div class="form-group">
                            <label>超卖阈值:</label>
                            <input type="number" id="rsi_oversold" value="30" min="10" max="50">
                        </div>
                    `;
                    break;
            }
            
            paramsDiv.innerHTML = paramsHtml;
        }
        
        // 添加任务按钮点击事件
        addTaskBtn.addEventListener('click', () => {
            const strategy = strategySelect.value;
            const symbol = symbolSelect.value;
            
            if (!strategy || !symbol) return;
            
            // 创建新任务
            addLiveTask(strategy, symbol);
        });
        
        // 添加实盘任务
        function addLiveTask(strategy, symbol) {
            const tasksList = document.getElementById('live-tasks-list');
            const taskId = `task-${Date.now()}`;
            
            const strategyNames = {
                'ma_cross': 'MA均线策略',
                'bollinger': '布林带策略',
                'rsi': 'RSI策略'
            };
            
            const symbolNames = {
                'rb2405': '螺纹钢',
                'cu2405': '沪铜',
                'al2405': '沪铝'
            };
            
            // 获取策略参数
            let paramsText = '';
            switch (strategy) {
                case 'ma_cross':
                    const fastMa = document.getElementById('fast_ma')?.value || 5;
                    const slowMa = document.getElementById('slow_ma')?.value || 20;
                    paramsText = `快线:${fastMa} 慢线:${slowMa}`;
                    break;
                case 'bollinger':
                    const bbPeriod = document.getElementById('bb_period')?.value || 20;
                    const bbStd = document.getElementById('bb_std')?.value || 2;
                    paramsText = `周期:${bbPeriod} 标准差:${bbStd}`;
                    break;
                case 'rsi':
                    const rsiPeriod = document.getElementById('rsi_period')?.value || 14;
                    const overbought = document.getElementById('rsi_overbought')?.value || 70;
                    const oversold = document.getElementById('rsi_oversold')?.value || 30;
                    paramsText = `周期:${rsiPeriod} 超买:${overbought} 超卖:${oversold}`;
                    break;
                default:
                    paramsText = '默认参数';
            }
            
            const taskHtml = `
                <div class="task-item" data-task-id="${taskId}">
                    <div class="task-info">
                        <h4>${strategyNames[strategy]} - ${symbolNames[symbol]}</h4>
                        <p>${paramsText} | 运行时间: 刚刚启动</p>
                    </div>
                    <div class="task-status">
                        <span class="status-indicator status-running"></span>
                        <span style="font-size: 12px; color: #48bb78;">运行中</span>
                        <div class="task-controls">
                            <button class="task-btn task-btn-pause" onclick="pauseTask('${taskId}')">暂停</button>
                            <button class="task-btn task-btn-delete" onclick="deleteTask('${taskId}')">删除</button>
                        </div>
                    </div>
                </div>
            `;
            
            tasksList.insertAdjacentHTML('afterbegin', taskHtml);
            
            // 绑定点击事件
            const newTask = tasksList.querySelector(`[data-task-id="${taskId}"]`);
            newTask.addEventListener('click', (e) => {
                // 如果点击的是控制按钮，不触发任务选择
                if (e.target.classList.contains('task-btn')) {
                    e.stopPropagation();
                    return;
                }
                selectTask(taskId);
            });
            
            // 重置表单
            strategySelect.value = '';
            symbolSelect.value = '';
            checkFormComplete();
            
            alert(`✅ 成功添加 ${strategyNames[strategy]} 到实盘运行！`);
        }
        
        // ========== 任务选择和图表显示 ==========
        let selectedTaskId = null;
        
        // 绑定现有任务点击事件
        document.querySelectorAll('.task-item').forEach(item => {
            item.addEventListener('click', (e) => {
                // 如果点击的是控制按钮，不触发任务选择
                if (e.target.classList.contains('task-btn')) {
                    e.stopPropagation();
                    return;
                }
                const taskId = item.dataset.taskId;
                selectTask(taskId);
            });
        });
        
        function selectTask(taskId) {
            selectedTaskId = taskId;
            
            // 更新任务选择状态
            document.querySelectorAll('.task-item').forEach(item => {
                item.classList.remove('selected');
            });
            document.querySelector(`[data-task-id="${taskId}"]`).classList.add('selected');
            
            // 显示对应的图表
            loadLiveChart(taskId);
        }
        
        // ========== 任务控制功能 ==========
        function pauseTask(taskId) {
            console.log('暂停任务:', taskId);
            
            // 更新任务状态显示
            const taskItem = document.querySelector(`[data-task-id="${taskId}"]`);
            const statusIndicator = taskItem.querySelector('.status-indicator');
            const statusText = taskItem.querySelector('.task-status span:nth-child(2)');
            const controlsDiv = taskItem.querySelector('.task-controls');
            
            // 更新状态
            statusIndicator.className = 'status-indicator status-paused';
            statusText.textContent = '暂停';
            statusText.style.color = '#ed8936';
            
            // 更新按钮
            controlsDiv.innerHTML = `
                <button class="task-btn task-btn-resume" onclick="resumeTask('${taskId}')">恢复</button>
                <button class="task-btn task-btn-delete" onclick="deleteTask('${taskId}')">删除</button>
            `;
            
            // 这里可以添加实际的暂停逻辑，比如发送WebSocket消息
            alert(`✅ 已暂停任务: ${taskId}`);
        }
        
        function resumeTask(taskId) {
            console.log('恢复任务:', taskId);
            
            // 更新任务状态显示
            const taskItem = document.querySelector(`[data-task-id="${taskId}"]`);
            const statusIndicator = taskItem.querySelector('.status-indicator');
            const statusText = taskItem.querySelector('.task-status span:nth-child(2)');
            const controlsDiv = taskItem.querySelector('.task-controls');
            
            // 更新状态
            statusIndicator.className = 'status-indicator status-running';
            statusText.textContent = '运行中';
            statusText.style.color = '#48bb78';
            
            // 更新按钮
            controlsDiv.innerHTML = `
                <button class="task-btn task-btn-pause" onclick="pauseTask('${taskId}')">暂停</button>
                <button class="task-btn task-btn-delete" onclick="deleteTask('${taskId}')">删除</button>
            `;
            
            // 这里可以添加实际的恢复逻辑，比如发送WebSocket消息
            alert(`✅ 已恢复任务: ${taskId}`);
        }
        
        function deleteTask(taskId) {
            if (confirm(`确定要删除任务 ${taskId} 吗？此操作不可撤销！`)) {
                console.log('删除任务:', taskId);
                
                // 从DOM中移除任务项
                const taskItem = document.querySelector(`[data-task-id="${taskId}"]`);
                taskItem.remove();
                
                // 如果删除的是当前选中的任务，清空图表
                if (selectedTaskId === taskId) {
                    selectedTaskId = null;
                    const placeholder = document.getElementById('live-chart-placeholder');
                    const canvas = document.getElementById('liveChart');
                    
                    placeholder.style.display = 'flex';
                    canvas.style.display = 'none';
                }
                
                // 这里可以添加实际的删除逻辑，比如发送WebSocket消息
                alert(`✅ 已删除任务: ${taskId}`);
            }
        }
        
        function loadLiveChart(taskId) {
            const placeholder = document.getElementById('live-chart-placeholder');
            const canvas = document.getElementById('liveChart');
            
            placeholder.style.display = 'none';
            canvas.style.display = 'block';
            
            // 这里可以加载对应任务的实际图表数据
            // 目前显示演示图表
            createDemoLiveChart();
        }
        
        function createDemoLiveChart() {
            const ctx = document.getElementById('liveChart').getContext('2d');
            
            // 生成演示数据
            const labels = [];
            const priceData = [];
            const basePrice = 3500;
            
            for (let i = 0; i < 50; i++) {
                const time = new Date(Date.now() - (50 - i) * 60000);
                labels.push(time.toLocaleTimeString());
                priceData.push(basePrice + Math.sin(i / 5) * 50 + Math.random() * 20);
            }
            
            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: '实时价格',
                        data: priceData,
                        borderColor: '#5a67d8',
                        backgroundColor: 'rgba(90, 103, 216, 0.1)',
                        fill: true,
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: false,
                            title: {
                                display: true,
                                text: '价格'
                            }
                        },
                        x: {
                            title: {
                                display: true,
                                text: '时间'
                            }
                        }
                    },
                    plugins: {
                        title: {
                            display: true,
                            text: `📊 ${selectedTaskId ? selectedTaskId.toUpperCase() : '演示任务'} - 实时K线图表`
                        }
                    }
                }
            });
        }
        
        // ========== 回测功能 ==========
        function loadBacktestChart() {
            const statusElement = document.getElementById('backtest-chart-status');
            statusElement.textContent = '正在加载回测数据...';
            statusElement.style.color = '#5a67d8';
            
            fetch('/api/backtest/chart_data')
                .then(response => response.json())
                .then(data => {
                    createBacktestChart(data);
                    statusElement.textContent = '回测数据加载完成';
                    statusElement.style.color = '#48bb78';
                })
                .catch(error => {
                    console.error('Error loading backtest chart:', error);
                    statusElement.textContent = '数据加载失败';
                    statusElement.style.color = '#f56565';
                });
        }
        
        let backtestChart = null;
        
        function createBacktestChart(data) {
            const ctx = document.getElementById('backtestChart').getContext('2d');
            
            // 销毁现有图表
            if (backtestChart) {
                backtestChart.destroy();
            }
            
            // 简化数据处理
            const labels = data.kline_data.map((item, index) => {
                return index % 50 === 0 ? item.time.substring(5, 16) : '';
            });
            
            const priceData = data.kline_data.map(item => item.close);
            
            backtestChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'K线收盘价',
                        data: priceData,
                        borderColor: '#4299e1',
                        backgroundColor: 'rgba(66, 153, 225, 0.1)',
                        fill: false,
                        tension: 0.1,
                        pointRadius: 0,
                        borderWidth: 1.5
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: false,
                            title: {
                                display: true,
                                text: '价格 (元/吨)'
                            }
                        },
                        x: {
                            title: {
                                display: true,
                                text: '时间'
                            }
                        }
                    },
                    plugins: {
                        title: {
                            display: true,
                            text: '📊 回测分析图表 - K线图与交易信号'
                        }
                    }
                }
            });
        }
        
        // ========== WebSocket连接 ==========
        const socket = io();
        const connectionStatus = document.getElementById('connection-status');
        
        // 连接状态管理
        socket.on('connect', () => {
            connectionStatus.textContent = '已连接';
            connectionStatus.className = 'connected';
            console.log('已连接到服务器');
        });
        
        socket.on('disconnect', () => {
            connectionStatus.textContent = '未连接';
            connectionStatus.className = 'disconnected';
        });
        
        // ========== 用户管理数据加载 ==========
        function loadManagementData() {
            console.log('Loading management data...');
            
            // 加载投资组合配置
            loadPortfolioConfig();
            // 加载实时持仓
            loadPositionsData();
            // 加载成交记录
            loadTradesData();
            // 加载市场数据
            loadMarketData();
            // 加载策略状态
            loadStrategyStatus();
        }
        
        function loadPortfolioConfig() {
            const portfolioDiv = document.getElementById('portfolio-config');
            portfolioDiv.innerHTML = `
                <div class="config-table">
                    <div class="config-row">
                        <span>总资金:</span>
                        <span>¥1,000,000</span>
                    </div>
                    <div class="config-row">
                        <span>可用资金:</span>
                        <span>¥850,000</span>
                    </div>
                    <div class="config-row">
                        <span>持仓资金:</span>
                        <span>¥150,000</span>
                    </div>
                    <div class="config-row">
                        <span>风险等级:</span>
                        <span>中等</span>
                    </div>
                </div>
            `;
        }
        
        function loadPositionsData() {
            const positionsDiv = document.getElementById('positions-data');
            positionsDiv.innerHTML = `
                <div class="positions-table">
                    <div class="table-header">
                        <span>品种</span>
                        <span>方向</span>
                        <span>数量</span>
                        <span>开仓价</span>
                        <span>现价</span>
                        <span>盈亏</span>
                    </div>
                    <div class="table-row">
                        <span>螺纹钢2405</span>
                        <span class="long">多</span>
                        <span>2手</span>
                        <span>3500</span>
                        <span>3520</span>
                        <span class="profit">+400</span>
                    </div>
                    <div class="table-row">
                        <span>沪铜2405</span>
                        <span class="short">空</span>
                        <span>1手</span>
                        <span>71200</span>
                        <span>71100</span>
                        <span class="profit">+500</span>
                    </div>
                </div>
            `;
        }
        
        function loadTradesData() {
            const tradesDiv = document.getElementById('trades-data');
            tradesDiv.innerHTML = `
                <div class="trades-table">
                    <div class="table-header">
                        <span>时间</span>
                        <span>品种</span>
                        <span>方向</span>
                        <span>数量</span>
                        <span>价格</span>
                        <span>策略</span>
                    </div>
                    <div class="table-row">
                        <span>14:32:15</span>
                        <span>螺纹钢2405</span>
                        <span class="long">买入</span>
                        <span>1手</span>
                        <span>3520</span>
                        <span>MA策略</span>
                    </div>
                    <div class="table-row">
                        <span>13:45:22</span>
                        <span>沪铜2405</span>
                        <span class="short">卖出</span>
                        <span>1手</span>
                        <span>71100</span>
                        <span>布林带策略</span>
                    </div>
                    <div class="table-row">
                        <span>12:18:33</span>
                        <span>沪铝2405</span>
                        <span class="long">买入</span>
                        <span>2手</span>
                        <span>19850</span>
                        <span>RSI策略</span>
                    </div>
                </div>
            `;
        }
        
        function loadMarketData() {
            const marketDiv = document.getElementById('market-data');
            marketDiv.innerHTML = `
                <div class="market-table">
                    <div class="table-header">
                        <span>品种</span>
                        <span>最新价</span>
                        <span>涨跌</span>
                        <span>涨跌幅</span>
                        <span>成交量</span>
                    </div>
                    <div class="table-row">
                        <span>螺纹钢2405</span>
                        <span>3520</span>
                        <span class="profit">+15</span>
                        <span class="profit">+0.43%</span>
                        <span>1.2万手</span>
                    </div>
                    <div class="table-row">
                        <span>沪铜2405</span>
                        <span>71100</span>
                        <span class="loss">-50</span>
                        <span class="loss">-0.07%</span>
                        <span>8.5千手</span>
                    </div>
                    <div class="table-row">
                        <span>沪铝2405</span>
                        <span>19850</span>
                        <span class="profit">+25</span>
                        <span class="profit">+0.13%</span>
                        <span>6.2千手</span>
                    </div>
                </div>
            `;
        }
        
        function loadStrategyStatus() {
            const strategyDiv = document.getElementById('strategy-status');
            strategyDiv.innerHTML = `
                <div class="strategy-table">
                    <div class="table-header">
                        <span>策略名称</span>
                        <span>状态</span>
                        <span>运行时间</span>
                        <span>今日盈亏</span>
                        <span>胜率</span>
                    </div>
                    <div class="table-row">
                        <span>MA均线策略</span>
                        <span class="status-running">运行中</span>
                        <span>2小时36分</span>
                        <span class="profit">+1,250</span>
                        <span>65%</span>
                    </div>
                    <div class="table-row">
                        <span>布林带策略</span>
                        <span class="status-paused">暂停</span>
                        <span>45分钟</span>
                        <span class="profit">+800</span>
                        <span>72%</span>
                    </div>
                    <div class="table-row">
                        <span>RSI策略</span>
                        <span class="status-stopped">已停止</span>
                        <span>1小时15分</span>
                        <span class="loss">-320</span>
                        <span>58%</span>
                    </div>
                </div>
            `;
        }
        
        // 页面加载完成后初始化
        document.addEventListener('DOMContentLoaded', () => {
            // 初始化策略参数配置区域
            const paramsDiv = document.getElementById('strategy-params');
            if (paramsDiv) {
                paramsDiv.innerHTML = '<p style="color: #718096; font-size: 13px; text-align: center; padding: 20px;">请先选择策略类型...</p>';
            }
            
            // 默认选择第一个任务显示图表
            setTimeout(() => {
                const firstTask = document.querySelector('.task-item[data-task-id]');
                if (firstTask && !selectedTaskId) {
                    const taskId = firstTask.dataset.taskId;
                    selectTask(taskId);
                }
            }, 500);
        });
