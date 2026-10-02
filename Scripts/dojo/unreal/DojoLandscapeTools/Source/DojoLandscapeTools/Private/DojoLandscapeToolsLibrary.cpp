#include "DojoLandscapeToolsLibrary.h"

#include "Editor.h"
#include "Engine/World.h"
#include "Landscape.h"
#include "LandscapeInfo.h"
#include "LandscapeProxy.h"
#include "Materials/MaterialInterface.h"
#include "Misc/FileHelper.h"
#include "RenderingThread.h"

ALandscape* UDojoLandscapeToolsLibrary::CreateLandscapeFromRaw16(const FString& RawPath, int32 SizeX, int32 SizeY,
	int32 SectionsPerComponent, int32 QuadsPerSection, FVector Location, FVector Scale, UMaterialInterface* Material,
	const FString& Label, FString& OutReport)
{
	UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
	if (!World)
	{
		OutReport = TEXT("no editor world");
		return nullptr;
	}
	const int32 QuadsPerComponent = SectionsPerComponent * QuadsPerSection;
	if (QuadsPerComponent <= 0 || (SizeX - 1) % QuadsPerComponent != 0 || (SizeY - 1) % QuadsPerComponent != 0)
	{
		OutReport = FString::Printf(TEXT("size %d x %d is not a whole number of %d-quad components"), SizeX, SizeY, QuadsPerComponent);
		return nullptr;
	}
	TArray<uint8> Bytes;
	if (!FFileHelper::LoadFileToArray(Bytes, *RawPath))
	{
		OutReport = FString::Printf(TEXT("cannot read %s"), *RawPath);
		return nullptr;
	}
	const int64 Want = int64(SizeX) * int64(SizeY) * 2;
	if (Bytes.Num() != Want)
	{
		OutReport = FString::Printf(TEXT("%s has %d bytes, want %lld"), *RawPath, Bytes.Num(), Want);
		return nullptr;
	}
	TArray<uint16> Heights;
	Heights.SetNumUninitialized(SizeX * SizeY);
	FMemory::Memcpy(Heights.GetData(), Bytes.GetData(), Bytes.Num());

	ALandscape* Landscape = World->SpawnActor<ALandscape>(Location, FRotator::ZeroRotator);
	if (!Landscape)
	{
		OutReport = TEXT("SpawnActor<ALandscape> failed");
		return nullptr;
	}
	Landscape->LandscapeMaterial = Material;
	Landscape->SetActorRelativeScale3D(Scale);

	TMap<FGuid, TArray<uint16>> HeightDataPerLayers;
	HeightDataPerLayers.Add(FGuid(), MoveTemp(Heights));
	TMap<FGuid, TArray<FLandscapeImportLayerInfo>> MaterialLayerDataPerLayers;
	MaterialLayerDataPerLayers.Add(FGuid(), TArray<FLandscapeImportLayerInfo>());

	Landscape->Import(FGuid::NewGuid(), 0, 0, SizeX - 1, SizeY - 1, SectionsPerComponent, QuadsPerSection,
		HeightDataPerLayers, TEXT(""), MaterialLayerDataPerLayers, ELandscapeImportAlphamapType::Additive,
		TArrayView<const FLandscapeLayer>());

	ULandscapeInfo* Info = Landscape->GetLandscapeInfo();
	if (Info)
	{
		Info->UpdateLayerInfoMap(Landscape);
	}
	if (!Label.IsEmpty())
	{
		Landscape->SetActorLabel(Label);
	}
	OutReport = FString::Printf(TEXT("ok: %d components, %d x %d vertices, %d sections x %d quads"),
		Landscape->LandscapeComponents.Num(), SizeX, SizeY, SectionsPerComponent, QuadsPerSection);
	return Landscape;
}

FString UDojoLandscapeToolsLibrary::FinalizeLandscape(ALandscape* Landscape, bool bBuildNanite)
{
	if (!Landscape)
	{
		return TEXT("no landscape");
	}
	Landscape->ForceLayersFullUpdate();
	Landscape->ForceUpdateLayersContent();
	FlushRenderingCommands();
	Landscape->RecreateCollisionComponents();
	FString Nanite = TEXT("nanite off");
	if (bBuildNanite && Landscape->IsNaniteEnabled())
	{
		Landscape->UpdateNaniteRepresentation(nullptr);
		FlushRenderingCommands();
		Nanite = Landscape->IsNaniteMeshUpToDate() ? TEXT("nanite up to date") : TEXT("nanite NOT up to date");
	}
	return FString::Printf(TEXT("finalized: layers merged, collision rebuilt, %s"), *Nanite);
}
