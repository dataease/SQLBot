const {checkIsPercent} = require("./utils");

function getLineOptions(baseOptions, axis, data) {

    const x = axis.filter((item) => item.type === 'x')
    const y = axis.filter((item) => item.type === 'y')
    const series = axis.filter((item) => item.type === 'series')

    if (x.length === 0 || y.length === 0) {
        return
    }

    const _data = checkIsPercent(y[0], data)

    const options = {
        ...baseOptions,
        type: 'view',
        data: _data.data,
        encode: {
            x: x[0].value,
            y: y[0].value,
            color: series.length > 0 ? series[0].value : undefined,
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
        children: [
            {
                type: 'line',
                encode: {
                    shape: 'smooth',
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
                        style: {
                            dx: -10,
                            dy: -12,
                        },
                        transform: [
                            {type: 'contrastReverse'},
                            {type: 'exceedAdjust'},
                            {type: 'overlapHide'},
                        ],
                    },
                ],
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
            },
            {
                type: 'point',
                style: {
                    fill: 'white',
                },
                encode: {
                    size: 1.5,
                },
                tooltip: false,
            },
        ],
    }

    return options
}

module.exports = {getLineOptions}
