const http = require('http');
const url = require("url");
const util = require('util');
const { createChart } = require('@antv/g2-ssr');
const port = 3000;
const { getPieOptions } = require('./charts/pie.js');
const { getLineOptions } = require('./charts/line.js');
const { getColumnOptions } = require('./charts/column.js');
const { getBarOptions } = require('./charts/bar.js');
const { getScatterOptions } = require('./charts/scatter.js');

http.createServer((req, res) => {
    res.statusCode = 200,
        res.setHeader('Content-Type', 'text/plain;charset=utf-8');
    if (req.method === 'GET') {
        toGet(req, res);
    } else if (req.method === 'POST') {
        toPost(req, res);
    }
}).listen(port, () => {
    console.info(`Server listening on: http://localhost:${port}`);
});

function getOptions(type, axis, data) {

    const base_options = {
        width: 640,
        height: 480,
        imageType: 'png',
        theme: {
            view: {
                viewFill: '#FFFFFF',
            },
        }
    }

    switch (type) {
        case 'bar':
            return getBarOptions(base_options, axis, data);
        case 'column':
            return getColumnOptions(base_options, axis, data);
        case 'line':
            return getLineOptions(base_options, axis, data);
        case 'pie':
            return getPieOptions(base_options, axis, data);
        case 'scatter':
            return getScatterOptions(base_options, axis, data);
    }

    return base_options
}


// 创建 Chart 和配置
async function GenerateCharts(obj) {
    const options = getOptions(obj.type, JSON.parse(obj.axis), JSON.parse(obj.data));
    const chart = await createChart(options);
    // 导出
    chart.exportToFile(obj.path || 'chart');
    // -> chart.png
    chart.toBuffer();
}

// -> get buffer


//获取GET请求内容
function toGet(req, res) {
    let data = 'GET请求内容：\n' + util.inspect(url.parse(req.url));
    res.end(data);
}

//获取POST请求内容、cookie
function toPost(req, res) {
    const bodyChunks = []
    req.on('data', function (chunk) {
        bodyChunks.push(chunk)
    }).on('end', async () => {
        const completeBodyBuffer = Buffer.concat(bodyChunks);
        await GenerateCharts(JSON.parse(completeBodyBuffer.toString('utf8')))
        res.end('complete');
    });
}