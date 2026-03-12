import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

const instruments = [
  {
    symbol: 'SPY',
    name: 'SPDR S&P 500 ETF Trust',
    exchange: 'NYSE ARCA',
    type: 'ETF',
    currency: 'USD',
    fteThreshold: 0.05,
    minSignalDistance: 21,
  },
  {
    symbol: 'GLD',
    name: 'SPDR Gold Shares',
    exchange: 'NYSE ARCA',
    type: 'ETF',
    currency: 'USD',
    fteThreshold: 0.05,
    minSignalDistance: 21,
  },
  {
    symbol: 'BTC-USD',
    name: 'Bitcoin USD',
    exchange: 'CRYPTO',
    type: 'CRYPTO',
    currency: 'USD',
    proxyType: 'TRUST',
    signalDirection: -1, // Inverse for GBTC
    fteThreshold: 0.08,
    minSignalDistance: 21,
  },
  {
    symbol: 'GBTC',
    name: 'Grayscale Bitcoin Trust',
    exchange: 'OTC',
    type: 'TRUST',
    currency: 'USD',
    proxyType: 'TRUST',
    regimeChangeDate: new Date('2024-01-11'),
    signalDirection: -1,
    fteThreshold: 0.08,
    minSignalDistance: 21,
  },
  {
    symbol: 'GC=F',
    name: 'Gold Futures',
    exchange: 'COMEX',
    type: 'FUTURES',
    currency: 'USD',
    fteThreshold: 0.05,
    minSignalDistance: 21,
  },
]

async function main() {
  console.log('Seeding instruments...')
  
  for (const instrument of instruments) {
    await prisma.instrument.upsert({
      where: { symbol: instrument.symbol },
      update: instrument,
      create: instrument,
    })
    console.log(`  ✓ ${instrument.symbol}`)
  }
  
  console.log('\nSeeding complete!')
  
  // Print summary
  const count = await prisma.instrument.count()
  console.log(`Total instruments: ${count}`)
}

main()
  .catch((e) => {
    console.error(e)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
