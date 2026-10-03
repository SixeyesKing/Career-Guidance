---
id: guide-前端面试高频问题-frontend
title: 前端面试高频问题
job_category: frontend
document_type: interview_preparation
source_name: 牛客网、前端面试题汇总
source_url: https://www.nowcoder.com/discuss/tag/637
updated_at: 未提供
review_status: not_reviewed
freshness: general
content_kind: guide
is_placeholder: false
---

适用岗位：前端开发

# 前端面试高频问题

## 岗位类别
前端开发

## 资料类型
面试准备

## 正文内容

### 一、HTML/CSS

#### 1. 什么是盒模型？
A：
- 标准盒模型：width/height只包含content
- IE盒模型：width/height包含content + padding + border
- box-sizing：content-box（标准）、border-box（IE）

#### 2. Flex布局常用属性？
A：
- 容器属性：flex-direction、flex-wrap、justify-content、align-items、align-content
- 项目属性：flex-grow、flex-shrink、flex-basis、align-self

#### 3. 如何实现水平垂直居中？
A：
- Flex：display:flex; justify-content:center; align-items:center;
- Grid：display:grid; place-items:center;
- 定位：position:absolute; top:50%; left:50%; transform:translate(-50%,-50%)

#### 4. 什么是BFC？
A：
- Block Formatting Context（块级格式化上下文）
- 独立的渲染区域，内部元素不影响外部
- 触发条件：float、position、overflow、display等

### 二、JavaScript

#### 1. var、let、const的区别？
A：
- var：函数作用域，有变量提升
- let：块级作用域，无变量提升，不可重复声明
- const：块级作用域，无变量提升，不可重复声明，不可重新赋值

#### 2. 什么是闭包？
A：
- 函数和其词法环境的组合
- 可以访问外部函数的变量
- 应用：数据私有化、函数工厂

#### 3. 原型和原型链？
A：
- 每个对象都有__proto__属性指向其构造函数的prototype
- 原型链：通过__proto__形成的链式结构
- 继承：通过原型链实现

#### 4. Promise是什么？
A：
- 异步编程的解决方案
- 三种状态：pending、fulfilled、rejected
- 链式调用：.then().catch().finally()

#### 5. async/await是什么？
A：
- Promise的语法糖
- async函数返回Promise
- await等待Promise完成

#### 6. 事件循环（Event Loop）？
A：
- JavaScript是单线程
- 同步代码直接执行
- 异步代码放入任务队列
- 微任务（Promise）优先于宏任务（setTimeout）

### 三、Vue

#### 1. Vue的生命周期？
A：
- beforeCreate → created → beforeMount → mounted
- beforeUpdate → updated
- beforeDestroy → destroyed

#### 2. Vue的双向绑定原理？
A：
- v-model是语法糖
- 数据劫持（Object.defineProperty / Proxy）
- 发布-订阅模式

#### 3. computed和watch的区别？
A：
- computed：计算属性，有缓存，依赖变化时重新计算
- watch：侦听器，监听数据变化，执行回调

#### 4. Vue的组件通信方式？
A：
- props/$emit
- $parent/$children
- $refs
- provide/inject
- Vuex/Pinia

### 四、React

#### 1. React的生命周期？
A：
- 挂载：constructor → render → componentDidMount
- 更新：shouldComponentUpdate → render → componentDidUpdate
- 卸载：componentWillUnmount

#### 2. Hooks是什么？
A：
- 函数组件的状态管理
- useState、useEffect、useContext等
- 自定义Hook

#### 3. 虚拟DOM是什么？
A：
- JavaScript对象表示DOM结构
- Diff算法比较差异
- 批量更新真实DOM

### 五、计算机网络

#### 1. HTTP和HTTPS的区别？
A：
- HTTP：明文传输、端口80
- HTTPS：加密传输、端口443、需要证书
- HTTPS = HTTP + SSL/TLS

#### 2. TCP三次握手？
A：
1. 客户端发送SYN
2. 服务端发送SYN+ACK
3. 客户端发送ACK

#### 3. 跨域是什么？如何解决？
A：
- 同源策略限制
- 解决方案：CORS、JSONP、代理

### 六、性能优化

#### 1. 前端性能优化方法？
A：
- 减少HTTP请求
- 使用CDN
- 代码压缩
- 图片优化
- 懒加载
- 防抖节流

#### 2. 什么是防抖和节流？
A：
- 防抖：连续触发时，只执行最后一次
- 节流：连续触发时，每隔一段时间执行一次

### 七、来源信息

**来源名称**：牛客网、前端面试题汇总

**来源链接**：
- 牛客网面经：https://www.nowcoder.com/discuss/tag/637

**发布时间**：2026年

**整理时间**：2026-10-01
