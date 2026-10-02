#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "DojoLandscapeToolsLibrary.generated.h"

class ALandscape;
class UMaterialInterface;

UCLASS()
class UDojoLandscapeToolsLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()
public:
	/** Spawns a Landscape in the editor world and imports a raw little-endian uint16 heightmap (SizeX x SizeY
	 *  vertices, row-major, row 0 = the landscape's local -Y edge) exactly as the editor's New Landscape > Import does.
	 *  SizeX - 1 and SizeY - 1 must be multiples of SectionsPerComponent * QuadsPerSection. Height h (uint16) maps to
	 *  local z = (h - 32768) / 128 * Scale.Z cm. Returns the landscape (nullptr on failure, reason in OutReport). */
	UFUNCTION(BlueprintCallable, Category = "Dojo|Landscape")
	static ALandscape* CreateLandscapeFromRaw16(const FString& RawPath, int32 SizeX, int32 SizeY, int32 SectionsPerComponent,
		int32 QuadsPerSection, FVector Location, FVector Scale, UMaterialInterface* Material, const FString& Label,
		FString& OutReport);

	/** Forces the edit-layer merge (heights to the final heightmaps), rebuilds collision and, if Nanite is enabled on
	 *  the landscape, builds its Nanite representation now. Needs a real RHI (commandlet -AllowCommandletRendering). */
	UFUNCTION(BlueprintCallable, Category = "Dojo|Landscape")
	static FString FinalizeLandscape(ALandscape* Landscape, bool bBuildNanite);
};
