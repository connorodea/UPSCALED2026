import { NextRequest, NextResponse } from 'next/server';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ sku: string }> }
) {
  try {
    const { sku } = await params;

    if (!sku) {
      return NextResponse.json(
        { error: 'SKU is required' },
        { status: 400 }
      );
    }

    // TODO: Query database for marketplace listings
    // For now, return mock data for demonstration
    console.log(`[Marketplace Status] Fetching status for SKU: ${sku}`);

    // In production, this would query the marketplace_listings table
    // const listings = await prisma.marketplaceListing.findMany({
    //   where: { product: { sku } },
    //   include: { product: true }
    // });

    // Mock response - empty listings (product not cross-listed yet)
    const mockListings = [];

    return NextResponse.json({
      sku,
      listings: mockListings,
    });
  } catch (error: any) {
    console.error('[Marketplace Status] Error:', error);
    return NextResponse.json(
      { error: 'Failed to fetch marketplace status' },
      { status: 500 }
    );
  }
}
