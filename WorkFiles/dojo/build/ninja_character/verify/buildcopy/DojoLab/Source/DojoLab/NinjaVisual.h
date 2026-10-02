// Copyright Epic Games, Inc. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"

class AActor;
class UAnimInstance;
class UAnimMontage;
class UAnimSequenceBase;
class USkeletalMeshComponent;

/**
 * The ninja is Epic's Game Animation Sample character (BP_NinjaGasp, 2026-09-19): its Mesh is a HIDDEN SK_UEFN_Mannequin that
 * motion matching animates, and what the player sees is a child actor (BP_NinjaVisual: Manny with ABP_NinjaVisual) that
 * retargets that pose live and layers our hand seals (UpperBody slot, NinjaSealWeight) and full-body moves (DefaultSlot) on top.
 * Our montages therefore play on the VISIBLE mesh, found here.
 */
namespace NinjaVisual
{
	/** Tag on the ChildActorComponent that holds the visible character. */
	DEMOGAME_1_API extern const FName VisualComponentTag;
	/** Slots of ABP_NinjaVisual: full body (finishers, the air-jump flip) and the seal layer (spine_01 up). */
	DEMOGAME_1_API extern const FName FullBodySlot;
	DEMOGAME_1_API extern const FName UpperBodySlot;
	/** The seal layer's weight variable in ABP_NinjaVisual. */
	DEMOGAME_1_API extern const FName SealWeightVariable;

	/** The visible skeletal mesh: the child actor under the component tagged VisualComponentTag, else the character's Mesh. */
	DEMOGAME_1_API USkeletalMeshComponent* FindVisualMesh(const AActor* Owner);

	/**
	 * Plays Animation as a dynamic montage on Mesh's SlotName without stopping the other slots' montages (the engine helper stops
	 * the whole slot group, and DefaultSlot and UpperBody share DefaultGroup). bLoop repeats its section until the montage is
	 * stopped (a looping montage never reaches its end, so it never blends out by itself). bAutoBlendOut false holds the last frame
	 * until the caller stops it (it must be set before Montage_Play, which copies it into the playing instance). Returns the
	 * montage, or null.
	 */
	DEMOGAME_1_API UAnimMontage* PlaySlotMontage(USkeletalMeshComponent* Mesh, UAnimSequenceBase* Animation, FName SlotName, float BlendInTime,
		float BlendOutTime, float PlayRate, float StartPosition = 0.0f, bool bLoop = false, bool bAutoBlendOut = true,
		float BlendOutTriggerTime = -1.0f);

	/** Stops every montage using SlotName on Mesh (also ones already blending out, shortening their fade to BlendOutTime). */
	DEMOGAME_1_API void StopSlotMontages(USkeletalMeshComponent* Mesh, FName SlotName, float BlendOutTime);

	/** Sets a float (or Blueprint double) variable on an anim instance by name; missing variables are ignored. */
	DEMOGAME_1_API void SetAnimFloat(UAnimInstance* AnimInstance, FName VariableName, float Value);

	/**
	 * Hides or shows the visible body whose animation host is VisualMesh (the shadow clone's reveal delay). When the visual actor has a
	 * UNinjaVisualBodyComponent this hides whichever body is showing, Manny or the MetaHuman; otherwise VisualMesh itself.
	 */
	DEMOGAME_1_API void SetVisualHidden(USkeletalMeshComponent* VisualMesh, bool bHidden);
}
