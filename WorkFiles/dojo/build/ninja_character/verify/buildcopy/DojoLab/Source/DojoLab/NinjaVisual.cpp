// Copyright Epic Games, Inc. All Rights Reserved.

#include "NinjaVisual.h"

#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "Animation/AnimSequenceBase.h"
#include "Components/ChildActorComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/Character.h"
#include "NinjaVisualBodyComponent.h"

namespace NinjaVisual
{
	const FName VisualComponentTag(TEXT("NinjaVisual"));
	const FName FullBodySlot(TEXT("DefaultSlot"));
	const FName UpperBodySlot(TEXT("UpperBody"));
	const FName SealWeightVariable(TEXT("NinjaSealWeight"));

	USkeletalMeshComponent* FindVisualMesh(const AActor* Owner)
	{
		if (!Owner)
		{
			return nullptr;
		}
		TInlineComponentArray<UChildActorComponent*> ChildActors(Owner);
		for (const UChildActorComponent* ChildActor : ChildActors)
		{
			if (ChildActor && ChildActor->ComponentHasTag(VisualComponentTag))
			{
				if (const AActor* Visual = ChildActor->GetChildActor())
				{
					if (USkeletalMeshComponent* Mesh = Visual->FindComponentByClass<USkeletalMeshComponent>())
					{
						return Mesh;
					}
				}
			}
		}
		const ACharacter* Character = Cast<ACharacter>(Owner);
		return Character ? Character->GetMesh() : nullptr;
	}

	UAnimMontage* PlaySlotMontage(USkeletalMeshComponent* Mesh, UAnimSequenceBase* Animation, FName SlotName, float BlendInTime, float BlendOutTime,
		float PlayRate, float StartPosition, bool bLoop, bool bAutoBlendOut, float BlendOutTriggerTime)
	{
		UAnimInstance* AnimInstance = Mesh ? Mesh->GetAnimInstance() : nullptr;
		if (!AnimInstance || !Animation || !Animation->GetSkeleton())
		{
			return nullptr;
		}
		// BlendOutTriggerTime >= 0: the auto blend-out starts that many seconds of play before the end and still lasts BlendOutTime
		// (AnimMontage.cpp: FAnimMontageInstance::Advance); -1 starts it BlendOutTime before the end.
		UAnimMontage* Montage = UAnimMontage::CreateSlotAnimationAsDynamicMontage(Animation, SlotName, BlendInTime, BlendOutTime, PlayRate,
			/*LoopCount*/ 1, BlendOutTriggerTime);
		if (!Montage)
		{
			return nullptr;
		}
		if (bLoop && Montage->CompositeSections.Num() > 0)
		{
			// A dynamic montage has one section; pointing it at itself repeats it.
			FCompositeSection& Section = Montage->CompositeSections[0];
			Section.NextSectionName = Section.SectionName;
		}
		// FAnimMontageInstance::Play copies this into the instance; writing the asset after Montage_Play has no effect.
		Montage->bEnableAutoBlendOut = bAutoBlendOut;
		StopSlotMontages(Mesh, SlotName, BlendInTime);
		const float PlayLength = AnimInstance->Montage_Play(Montage, PlayRate, EMontagePlayReturnType::MontageLength, StartPosition, /*bStopAllMontages*/ false);
		return PlayLength > 0.0f ? Montage : nullptr;
	}

	void StopSlotMontages(USkeletalMeshComponent* Mesh, FName SlotName, float BlendOutTime)
	{
		UAnimInstance* AnimInstance = Mesh ? Mesh->GetAnimInstance() : nullptr;
		if (!AnimInstance)
		{
			return;
		}
		// Backwards: stopping can fire blend-out events that change the array.
		for (int32 Index = AnimInstance->MontageInstances.Num() - 1; Index >= 0; --Index)
		{
			if (!AnimInstance->MontageInstances.IsValidIndex(Index))
			{
				continue;
			}
			FAnimMontageInstance* Instance = AnimInstance->MontageInstances[Index];
			if (Instance && Instance->Montage && Instance->Montage->IsValidSlot(SlotName))
			{
				Instance->Stop(FAlphaBlend(BlendOutTime), true);
			}
		}
	}

	void SetAnimFloat(UAnimInstance* AnimInstance, FName VariableName, float Value)
	{
		if (!AnimInstance)
		{
			return;
		}
		// Blueprint "float" variables are doubles in UE5; accept either.
		if (FDoubleProperty* DoubleProperty = FindFProperty<FDoubleProperty>(AnimInstance->GetClass(), VariableName))
		{
			DoubleProperty->SetPropertyValue_InContainer(AnimInstance, Value);
		}
		else if (FFloatProperty* FloatProperty = FindFProperty<FFloatProperty>(AnimInstance->GetClass(), VariableName))
		{
			FloatProperty->SetPropertyValue_InContainer(AnimInstance, Value);
		}
	}

	void SetVisualHidden(USkeletalMeshComponent* VisualMesh, bool bHidden)
	{
		if (!VisualMesh)
		{
			return;
		}
		// With a visual-body switch on the visual actor, whichever body is showing (Manny or the MetaHuman) is hidden.
		if (const AActor* Owner = VisualMesh->GetOwner())
		{
			if (UNinjaVisualBodyComponent* Body = Owner->FindComponentByClass<UNinjaVisualBodyComponent>())
			{
				Body->SetVisualSuppressed(bHidden);
				return;
			}
		}
		VisualMesh->SetHiddenInGame(bHidden);
	}
}
