const {checkIsPercent} = require("./utils");

function getBarOptions(baseOptions, axis, data) {

    const x = axis.filter((item) => item.type === 'x')
    const y = axis.filter((item) => item.type === 'y')
    const series = axis.filter((item) => item.type === 'series')

    if (x.length === 0 || y.length === 0) {
        return
    }

    const _data = checkIsPercent(y[0], data)

    const options = {
        ...baseOptions,
        type: 'interval',
        data: _data.data,
        coordinate: {transform: [{type: 'transpose'}]},
        encode: {
            x: x[0].value,
            y: y[0].value,
            color: series.length > 0 ? series[0].value : undefined,
        },
        style: {
            radiusTopLeft: (d) => {
                if (d[y[0].value] && d[y[0].value] > 0) {
                    return 4
                }
                return 0
            },
            radiusTopRight: (d) => {
                if (d[y[0].value] && d[y[0].value] > 0) {
                    return 4
                }
                return 0
            },
            radiusBottomLeft: (d) => {
                if (d[y[0].value] && d[y[0].value] < 0) {
                    return 4
                }
                return 0
            },
            radiusBottomRight: (d) => {
                if (d[y[0].value] && d[y[0].value] < 0) {
                    return 4
                }
                return 0
            },
        },
        axis: {
            x: {
                title: x[0].name,
                labelFontSize: 12,
                labelAutoHide: {
                    type: 'hide',
                    keepHeader: true,
                    keepTail: true,
                },
                labelAutoRotate: false,
                labelAutoWrap: true,
                labelAutoEllipsis: true,
            },
            y: {title: y[0].name},
        },
        scale: {
            x: {
                nice: true,
            },
            y: {
                nice: true,
                type: 'linear',
            },
        },
        interaction: {
            elementHighlight: {background: true},
        },
        tooltip: (data) => {
            if (series.length > 0) {
                return {
                    name: data[series[0].value],
                    value: `${data[y[0].value]}${_data.isPercent ? '%' : ''}`,
                }
            } else {
                return {name: y[0].name, value: `${data[y[0].value]}${_data.isPercent ? '%' : ''}`}
            }
        },
        labels: [
            {
                text: (data) => {
                    const value = data[y[0].value]
                    if (value === undefined || value === null) {
                        return ''
                    }
                    return `${value}${_data.isPercent ? '%' : ''}`
                },
                position: (data) => {
                    if (data[y[0].value] < 0) {
                        return 'bottom'
                    }
                    return 'top'
                },
                transform: [
                    {type: 'contrastReverse'},
                    {type: 'exceedAdjust'},
                    {type: 'overlapHide'},
                ],
            },
        ],
    }

    if (series.length > 0) {
        options.transform = [{type: 'stackY'}]
    }

    return options
}

module.exports = {getBarOptions}