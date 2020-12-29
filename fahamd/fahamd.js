
// derived from https://plotly.com/javascript/streaming/
'use strict'
const legend = 'slot'

async function fahData (key) {
  const path = 'api/fah/' + key
  const response = await fetch(path)
  const data = await response.json()
  return data
}

async function amdData (key) {
  const response = await fetch('api/amd/gpu')
  const data = await response.json()
  const gpus = await data.gpus
  const valueList = []
  for (const gpu of gpus) {
    valueList.push([gpu[key]])
  }
  return valueList
}

async function statusUpdate (traceInits) {
  fahData('gpu')
    .then(status => {
      for (let i = 0; i < gpuCount; i++) {
        const gpu = bus2gpu[busNumbers[i][0]]
        if (status[gpu] === 'RUNNING') {
          traceInits[i].line.dash = 'solid'
        } else if (status[gpu] === 'DOWNLOAD') {
          traceInits[i].line.dash = 'dash'
        } else {
          traceInits[i].line.dash = 'dot'
        }
      }
    })
}

// global variables
var busNumbers = null
var gpuCount = null
var bus2gpu = null
var gpu2slot = null

async function init () {
  const params = (new URL(window.location)).searchParams
  const field = params.get('field') || 'temperature'
  const layout = {
    title: { text: field },
    yaxis: { title: { text: field } }
  }
  busNumbers = await amdData('busNumber')
  gpuCount = busNumbers.length
  bus2gpu = await fahData('bus2gpu')
  gpu2slot = await fahData('gpu2slot')
  const dataPoints = await amdData(field)
  const traceInits = []
  const traceNumbers = []
  for (let i = 0; i < gpuCount; i++) {
    const time = new Date()
    let name = null
    if (legend === 'slot') {
      name = 'ID ' + gpu2slot[busNumbers[i][0]]
    } else if (legend === 'gpu') {
      name = 'gpu ' + bus2gpu[busNumbers[i][0]]
    } else {
      name = 'bus ' + busNumbers[i][0].toString()
    }
    const traceInit = {
      x: [time],
      y: dataPoints[i],
      name: name,
      type: 'line',
      mode: 'lines',
      line: { dash: 'dot' }
    }
    traceInits.push(traceInit)
    traceNumbers.push(i)
  }
  Plotly.plot('chart', traceInits, layout)
  let lastUpdate = 0
  setInterval(async function () {
    const time = new Date() // milliseconds
    if (time - lastUpdate >= 10000) {
      statusUpdate(traceInits)
      lastUpdate = new Date()
    }
    const update = {
      x: Array(gpuCount).fill([time]),
      y: await amdData(field)
    }
    const olderTime = time.setMinutes(time.getMinutes() - 1)
    const futureTime = time.setMinutes(time.getMinutes() + 1)
    const minuteView = {
      xaxis: {
        type: 'date',
        range: [olderTime, futureTime]
      }
    }
    Plotly.relayout('chart', minuteView)
    Plotly.extendTraces('chart', update, traceNumbers)
  }, 250)
}
